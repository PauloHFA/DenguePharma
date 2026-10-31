"""Curadoria clinica privada, transacional e append-only; nunca escreve no legado."""
from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager, nullcontext
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sqlite3
from uuid import uuid4

from ..domain import digest, json_bytes
from ..sources.snapshot import load_snapshot
from .effects import estimate, denominator
from .models import Principal, Screen, Result, Review, Conclusion, DocumentLink, Calibration, Absence, scope_for, scope_id, result_set_hash

REVIEW_ROLES = ("REVISOR", "ADJUDICADOR", "PESQUISADOR", "ADMINISTRADOR")
ADJUDICATORS = ("ADJUDICADOR", "ADMINISTRADOR")
SCHEMA_SQL = """
    CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT,id TEXT UNIQUE NOT NULL,kind TEXT NOT NULL,actor TEXT NOT NULL,roles TEXT NOT NULL,payload TEXT NOT NULL,previous_hash TEXT NOT NULL,event_hash TEXT NOT NULL,created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS sources(version_id TEXT PRIMARY KEY,document_id TEXT NOT NULL,content_hash TEXT NOT NULL,text_hash TEXT NOT NULL,text TEXT NOT NULL,license TEXT,access TEXT);
    CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'append-only'); END;
    CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'append-only'); END;
    CREATE TRIGGER IF NOT EXISTS sources_no_update BEFORE UPDATE ON sources BEGIN SELECT RAISE(ABORT,'append-only'); END;
    CREATE TRIGGER IF NOT EXISTS sources_no_delete BEFORE DELETE ON sources BEGIN SELECT RAISE(ABORT,'append-only'); END;
"""


def clinical_text(metadata):
    if "protocolSection" not in metadata:
        bibliographic={k:metadata[k] for k in ("pmid","pmcid","doi","journal","language","pub_year","publication_types","registry_ids","corrections","retractions") if k in metadata}
        return str(metadata.get("title", ""))+"\n"+str(metadata.get("abstract", ""))+"\n"+json.dumps(bibliographic,ensure_ascii=False,sort_keys=True)
    # Contatos/investigadores nao sao necessarios para revisao dos resultados.
    section = metadata["protocolSection"]
    safe = {k: section[k] for k in ("identificationModule", "descriptionModule", "statusModule", "designModule", "conditionsModule", "armsInterventionsModule", "outcomesModule", "eligibilityModule", "referencesModule") if k in section}
    if metadata.get("resultsSection"): safe["resultsSection"] = metadata["resultsSection"]
    return json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2)


def create(root: Path, snapshot, protocol: dict):
    if protocol.get("schema_version") != "clinical-protocol-1" or protocol["analysis"]["pooling"]: raise ValueError("UNSUPPORTED_PROTOCOL")
    key = digest(json_bytes({"input": snapshot.input_hash, "protocol": protocol}))
    folder = root.resolve() / "clinical" / key; folder.mkdir(parents=True, exist_ok=True)
    for name, content in (("input.json", snapshot.content), ("protocol.json", json_bytes(protocol))):
        try:
            with (folder/name).open("xb") as stream: stream.write(content)
        except FileExistsError:
            if (folder/name).read_bytes() != content: raise ValueError("IMMUTABLE_WORKSPACE_INPUT")
    with sqlite3.connect(folder/"curation.sqlite3") as db:
        db.executescript(SCHEMA_SQL)
    workspace = Workspace(root, key)
    # Metadados disponiveis no snapshot; abstracts ausentes nao sao inventados.
    for document in snapshot.data["documents"]:
        workspace.attach_source(document, clinical_text(document.get("metadata", {})))
    return workspace


class Workspace:
    def __init__(self, root: Path, key: str):
        if not re.fullmatch(r"[a-f0-9]{64}", key): raise ValueError("INVALID_WORKSPACE")
        self.root = root.resolve(); self.key = key; self.folder = self.root / "clinical" / key
        if not self.folder.resolve().is_relative_to(self.root): raise ValueError("UNSAFE_WORKSPACE")
        self.input = load_snapshot((self.folder/"input.json").read_bytes())
        self.protocol = json.loads((self.folder/"protocol.json").read_bytes())
        if digest(json_bytes({"input": self.input.input_hash, "protocol": self.protocol})) != key: raise ValueError("WORKSPACE_HASH_MISMATCH")

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.folder/"curation.sqlite3", timeout=30); db.row_factory = sqlite3.Row
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback(); raise
        finally: db.close()

    def events(self, db):
        result=[]; previous="0"*64
        for row in db.execute("SELECT * FROM events ORDER BY seq"):
            data={k:row[k] for k in ("id","kind","actor","roles","payload","previous_hash","created_at")}
            if row["previous_hash"] != previous or digest(json_bytes(data)) != row["event_hash"]: raise ValueError("AUDIT_CHAIN_INVALID")
            previous=row["event_hash"]; result.append({**dict(row),"payload":json.loads(row["payload"]),"roles":json.loads(row["roles"])})
        return result

    def append(self, db, kind, payload, actor):
        events=self.events(db)
        item={"id":str(uuid4()),"kind":kind,"actor":actor.id,"roles":json.dumps(sorted(actor.roles)),"payload":json.dumps(payload,ensure_ascii=False,sort_keys=True),
            "previous_hash":events[-1]["event_hash"] if events else "0"*64,"created_at":datetime.now(timezone.utc).isoformat()}
        db.execute("INSERT INTO events(id,kind,actor,roles,payload,previous_hash,event_hash,created_at) VALUES(?,?,?,?,?,?,?,?)",tuple(item[k] for k in ("id","kind","actor","roles","payload","previous_hash"))+(digest(json_bytes(item)),item["created_at"]))
        return item["id"]

    def attach_source(self, document, text):
        # Fonte normalizada e versionada; nunca substituir texto ja usado para revisar.
        text_hash=digest(text.encode()); version_id=document["versionId"]
        with self.transaction() as db:
            old=db.execute("SELECT * FROM sources WHERE version_id=?",(version_id,)).fetchone()
            if old:
                if old["content_hash"] != document["contentHash"]: raise ValueError("SOURCE_HASH_CONFLICT")
                if old["text_hash"] == text_hash: return version_id
                # Enriquecimento de metadados sanitizados para o original, em nova representacao.
                version_id=version_id+":"+text_hash[:16]
            db.execute("INSERT OR IGNORE INTO sources(version_id,document_id,content_hash,text_hash,text,license,access) VALUES(?,?,?,?,?,?,?)",(version_id,document["documentId"],document["contentHash"],text_hash,text,document.get("license"),document.get("accessStatus")))
        return version_id

    def initial_assignments(self):
        assignments={}
        for document in self.input.data["documents"]:
            confirmed={str(link["study_id"]) for link in document.get("studyLinks",[]) if link.get("link_certainty")=="CONFIRMADO"}
            # Referencias legadas divergentes nao escolhem silenciosamente o primeiro estudo.
            assignments[document["documentId"]]=next(iter(confirmed)) if len(confirmed)==1 else document["documentId"]
        return assignments

    def assignments(self,events):
        assignments=self.initial_assignments();revisions=defaultdict(list)
        for event in events:
            if event["kind"]!="DOCUMENT_LINKED":continue
            document=event["payload"]["document_id"];target=event["payload"]["study_id"]
            if document not in assignments:raise ValueError("UNKNOWN_DOCUMENT_LINK")
            previous=assignments[document]
            for study in {previous,target}:revisions[study].append(event["id"])
            assignments[document]=target
        return assignments,revisions

    def known_study_ids(self,events):
        return set(self.initial_assignments().values())|set(self.assignments(events)[0].values())|{str(link["study_id"]) for d in self.input.data["documents"] for link in d.get("studyLinks",[]) if link.get("link_certainty")=="CONFIRMADO"}

    def unresolved_identity(self,events):
        reviewed={e["payload"]["document_id"] for e in events if e["kind"]=="DOCUMENT_LINKED"}
        return sorted(d["documentId"] for d in self.input.data["documents"] if d["documentId"] not in reviewed and len({str(l["study_id"]) for l in d.get("studyLinks",[]) if l.get("link_certainty")=="CONFIRMADO"})>1)

    def catalog(self, events):
        assignments,_=self.assignments(events)
        catalog=defaultdict(list)
        for document in self.input.data["documents"]: catalog[assignments[document["documentId"]]].append(document)
        return dict(catalog)

    def basis(self, db, study_id, events):
        docs=self.catalog(events).get(study_id)
        if not docs: raise ValueError("UNKNOWN_STUDY")
        sources=[dict(row) for row in db.execute("SELECT document_id,version_id,text_hash FROM sources ORDER BY document_id,version_id") if row["document_id"] in {d["documentId"] for d in docs}]
        data={"documents":sorted(d["documentId"] for d in docs),"sources":sources}
        revisions=self.assignments(events)[1].get(study_id)
        if revisions:data["identity_revisions"]=revisions
        from .integrity import revisions as integrity_revisions
        integrity=integrity_revisions(events,set(data["documents"]))
        if integrity:data["integrity_revisions"]=integrity
        return digest(json_bytes(data))

    def screening(self, db, study_id, events):
        basis=self.basis(db,study_id,events); votes={}
        for e in events:
            p=e["payload"]
            if e["kind"]=="SCREENED" and p["study_id"]==study_id and p["basis_hash"]==basis: votes[e["actor"]]=e
        signature=digest(json_bytes(sorted(e["id"] for e in votes.values())))
        for e in reversed(events):
            p=e["payload"]
            if e["kind"]=="SCREEN_ADJUDICATED" and p["study_id"]==study_id and p["basis_hash"]==basis and p["votes_hash"]==signature:
                return {"status":p["decision"],"classification":p["classification"],"basis_hash":basis,"votes_hash":signature,"votes":votes}
        values={json.dumps({k:e["payload"][k] for k in ("decision","classification")},sort_keys=True) for e in votes.values()}
        status="PENDENTE" if len(votes)<2 else "CONFLITO" if len(values)>1 else next(iter(votes.values()))["payload"]["decision"]
        return {"status":status,"classification":next(iter(votes.values()))["payload"]["classification"] if status in {"INCLUIR","EXCLUIR"} else None,"basis_hash":basis,"votes_hash":signature,"votes":votes}

    def shadow_advisory(self, study_id, docs, basis_hash):
        from .shadow_screening import get_shadow_recommendation
        return get_shadow_recommendation(study_id, docs, basis_hash, self.protocol)

    def queue(self, actor):
        from .personal_review import assignment
        actor.require(*REVIEW_ROLES)
        with self.transaction() as db:
            events=self.events(db); rows=[]
            for study, docs in self.catalog(events).items():
                state=self.screening(db,study,events); own=state["votes"].get(actor.id)
                rows.append({"study_id":study,"title":docs[0].get("title"),"document_ids":[d["documentId"] for d in docs],"basis_hash":state["basis_hash"],"status":state["status"],
                    "personal_review":assignment(actor.id,study,state,events),
                    "can_adjudicate_screening":state["status"]=="CONFLITO" and bool(set(actor.roles).intersection(ADJUDICATORS)) and actor.id not in state["votes"],
                    "adjudication": {"votes_hash":state["votes_hash"],"votes":[e["payload"] for e in state["votes"].values()],"shadow_screening":self.shadow_advisory(study,docs,state["basis_hash"])} if state["status"]=="CONFLITO" and set(actor.roles).intersection(ADJUDICATORS) else None,
                    "own_decision":own["payload"] if own else None,"classification":state["classification"] if own or actor.roles and set(actor.roles).intersection(ADJUDICATORS) else None})
            return rows

    def source(self, version_id, actor):
        actor.require(*REVIEW_ROLES)
        with self.transaction() as db:
            row=db.execute("SELECT * FROM sources WHERE version_id=?",(version_id,)).fetchone()
            if not row: raise ValueError("SOURCE_NOT_FOUND")
            return dict(row)

    def validate_evidence(self, db, data, events):
        doc_ids={d["documentId"] for d in self.catalog(events)[data["study_id"]]}
        refs={}
        for ref in data["evidence"]:
            source=db.execute("SELECT * FROM sources WHERE version_id=?",(ref["version_id"],)).fetchone()
            if not source or source["document_id"] not in doc_ids or source["text_hash"]!=ref["text_hash"]: raise ValueError("EVIDENCE_VERSION_MISMATCH")
            if ref["end"]<=ref["start"] or source["text"][ref["start"]:ref["end"]]!=ref["quote"]: raise ValueError("LITERAL_EVIDENCE_REQUIRED")
            refs.setdefault(ref["field"],[]).append(ref["quote"])
        required={"intervention":data["intervention"],"comparator":data["comparator"],"population":None,"outcome_definition":None,"timepoint":None,"risk_of_bias":None}
        if data["effect_type"] in {"RR","MD"}:
            names=("n","events") if data["effect_type"]=="RR" else ("n","mean","sd")
            for arm in ("treatment","control"):
                for key in names: required[arm+"."+key]=data[arm][key]
        elif data["reported"] and data["reported"].get("estimate") is not None:
            for name in ("estimate","ci_low","ci_high"):
                if data["reported"].get(name) is not None: required["reported."+name]=data["reported"][name]
        for field,value in required.items():
            if field not in refs: raise ValueError("MISSING_FIELD_EVIDENCE:"+field)
            if isinstance(value,(int,float)) and not isinstance(value,bool):
                numbers=[float(x.replace(",",".")) for quote in refs[field] for x in re.findall(r"(?<![\w.])-?\d+(?:[.,]\d+)?(?![\w.])",quote)]
                if not any(abs(x-value)<1e-9 for x in numbers): raise ValueError("NUMBER_NOT_IN_EVIDENCE:"+field)

    def validate_result(self, db, payload, events):
        data=Result.model_validate(payload).model_dump(); state=self.screening(db,data["study_id"],events)
        from .integrity import blocked_documents
        if set(blocked_documents(events)).intersection(d["documentId"] for d in self.catalog(events)[data["study_id"]]):raise ValueError("DOCUMENT_INTEGRITY_REVIEW_REQUIRED")
        if state["status"]!="INCLUIR" or data["basis_hash"]!=state["basis_hash"]: raise ValueError("INCLUDED_CURRENT_STUDY_REQUIRED")
        c=state["classification"]
        for name in ("population","severity","disease_phase","purpose","design"):
            if data[name]!=c[name] and not (name=="population" and c[name]=="MISTA_SEM_SEPARACAO") and not (name in {"severity","disease_phase"} and c[name]=="MISTA"): raise ValueError("RESULT_CLASSIFICATION_MISMATCH:"+name)
        if data["intervention"].casefold() not in {v.casefold() for v in c["interventions"]}: raise ValueError("INTERVENTION_NOT_SCREENED")
        if data["outcome_code"] not in self.protocol["outcomes"]: raise ValueError("OUTCOME_NOT_IN_PROTOCOL")
        if data["risk_of_bias"]!="NAO_AVALIADO" and (not data["risk_of_bias_instrument"] or not data["risk_of_bias_domains"]): raise ValueError("METHODOLOGICAL_INSTRUMENT_AND_DOMAINS_REQUIRED")
        if data["supersedes"] and not any(e["id"]==data["supersedes"] and e["kind"]=="RESULT_DRAFTED" for e in events): raise ValueError("UNKNOWN_SUPERSEDED_RESULT")
        if data["supersedes"] and len(data.get("correction_reason") or "")<5: raise ValueError("CORRECTION_REASON_REQUIRED")
        if data["supersedes"]:
            prior=next(e["payload"] for e in events if e["id"]==data["supersedes"])
            if any(prior[k]!=data[k] for k in ("study_id","comparison_id","outcome_code","timepoint")): raise ValueError("CORRECTION_MUST_PRESERVE_COMPARISON_IDENTITY")
        for arm in (data["treatment"],data["control"]):
            if arm["n"] is not None:
                denominator(arm)
                if arm["events"] is not None and arm["events"]>arm["n"]: raise ValueError("EVENTS_EXCEED_DENOMINATOR")
        estimate(data)
        return data

    def validate_screen(self,db,payload,actor,events,*,adjudicate=False):
        actor.require(*REVIEW_ROLES)
        data=Screen.model_validate({k:v for k,v in payload.items() if k!="votes_hash"}).model_dump()
        state=self.screening(db,data["study_id"],events)
        if data["basis_hash"]!=state["basis_hash"]:raise ValueError("STALE_REVIEW_BASIS")
        from .integrity import blocked_documents
        if data["decision"]=="INCLUIR" and set(blocked_documents(events)).intersection(d["documentId"] for d in self.catalog(events)[data["study_id"]]):raise ValueError("DOCUMENT_INTEGRITY_REVIEW_REQUIRED")
        if data["decision"]=="INCLUIR" and set(self.unresolved_identity(events)).intersection(d["documentId"] for d in self.catalog(events)[data["study_id"]]):raise ValueError("AMBIGUOUS_DOCUMENT_IDENTITY")
        if not adjudicate:
            if len(state["votes"])>=2 and actor.id not in state["votes"]:raise ValueError("TWO_REVIEWERS_ALREADY_ASSIGNED")
        else:
            actor.require(*ADJUDICATORS)
            if state["status"]!="CONFLITO" or len(state["votes"])<2:raise ValueError("SCREENING_CONFLICT_REQUIRED")
            if actor.id in state["votes"]:raise PermissionError("INDEPENDENT_ADJUDICATOR_REQUIRED")
            if payload.get("votes_hash")!=state["votes_hash"]:raise ValueError("STALE_VOTE_SET")
            data["votes_hash"]=state["votes_hash"]
        return data

    def validate_document_link(self,payload,actor,events):
        actor.require(*ADJUDICATORS);data=DocumentLink.model_validate(payload).model_dump()
        assignments,_=self.assignments(events)
        if data["document_id"] not in assignments:raise ValueError("INVALID_DOCUMENT_LINK")
        if data["study_id"] not in self.known_study_ids(events):raise ValueError("UNKNOWN_STUDY")
        if assignments[data["document_id"]]==data["study_id"] and data["document_id"] not in self.unresolved_identity(events):raise ValueError("NO_IDENTITY_CHANGE")
        return data

    def act(self, kind, payload, actor, *, transaction=None):
        actor.require(*REVIEW_ROLES)
        with self.transaction() if transaction is None else nullcontext(transaction) as db:
            events=self.events(db)
            if kind in {"SCREENED","SCREEN_ADJUDICATED"}:
                data=self.validate_screen(db,payload,actor,events,adjudicate=kind=="SCREEN_ADJUDICATED")
            elif kind=="DOCUMENT_LINKED":
                data=self.validate_document_link(payload,actor,events)
            elif kind=="EXCLUSION_REASON_RECORDED":
                from .selection_flow import validate as validate_exclusion_reason
                data=validate_exclusion_reason(self,db,payload,actor,events)
            elif kind=="RESULT_DRAFTED":
                data=self.validate_result(db,payload,events)
            elif kind in {"RESULT_REVIEWED","RESULT_ADJUDICATED"}:
                data=Review.model_validate(payload).model_dump(); candidate=next((e for e in events if e["id"]==data["result_id"] and e["kind"]=="RESULT_DRAFTED"),None)
                if not candidate: raise ValueError("RESULT_NOT_FOUND")
                if actor.id==candidate["actor"]: raise PermissionError("SELF_REVIEW_FORBIDDEN")
                state=self.screening(db,candidate["payload"]["study_id"],events)
                if state["status"]!="INCLUIR" or state["basis_hash"]!=candidate["payload"]["basis_hash"]: raise ValueError("STALE_RESULT")
                self.validate_result(db,candidate["payload"],events)
                if kind=="RESULT_ADJUDICATED":
                    actor.require(*ADJUDICATORS)
                    reviews=[e for e in events if e["kind"]=="RESULT_REVIEWED" and e["payload"]["result_id"]==data["result_id"]]
                    if not reviews or reviews[-1]["payload"]["decision"]!="ACEITAR": raise ValueError("INDEPENDENT_REVIEW_REQUIRED")
                    if actor.id in {e["actor"] for e in reviews}: raise PermissionError("INDEPENDENT_ADJUDICATOR_REQUIRED")
                    if data["decision"]=="ACEITAR": self.validate_evidence(db,candidate["payload"],events)
            elif kind=="SYNTHESIS_CONCLUDED":
                actor.require(*ADJUDICATORS); data=Conclusion.model_validate(payload).model_dump()
                self.require_current_selection(db,events,data["selection_hash"],calibrated=True)
                _, groups, conflicts=self.results(db,events); group=next((g for g in groups if g["scope"]==data["scope"]),None)
                if conflicts: raise ValueError("UNRESOLVED_EXTRACTION_CONFLICTS")
                if not group or group["result_set_hash"]!=data["result_set_hash"]: raise ValueError("CURRENT_COMPLETE_RESULT_SET_REQUIRED")
                if data["category"]=="BENEFICIO_SUSTENTADO" and (group["scope"]["design_layer"]!="RCT" or any(r["risk_of_bias"]=="NAO_AVALIADO" for r in group["results"])): raise ValueError("REVIEWED_RANDOMIZED_EVIDENCE_REQUIRED")
            elif kind=="CALIBRATION_APPROVED":
                actor.require(*ADJUDICATORS); data=Calibration.model_validate(payload).model_dump()
                self.require_current_selection(db,events,data["selection_hash"])
                if len(data.get("reason",""))<10 or len(data.get("sentinel_ids",[]))<1: raise ValueError("DOCUMENTED_CALIBRATION_REQUIRED")
                if any(self.screening(db,s,events)["status"] not in {"INCLUIR","EXCLUIR"} for s in self.catalog(events)): raise ValueError("SCREENING_NOT_COMPLETE")
                if not set(data["sentinel_ids"]) <= set(self.catalog(events)): raise ValueError("UNKNOWN_SENTINEL")
                if len(set(data["sentinel_ids"]))!=len(data["sentinel_ids"]): raise ValueError("DUPLICATE_SENTINELS")
                data["basis_hash"]=self.selection_hash(db,events)
            elif kind=="ABSENCE_CONCLUDED":
                actor.require(*ADJUDICATORS); data=Absence.model_validate(payload).model_dump()
                self.require_current_selection(db,events,data["selection_hash"],calibrated=True)
                if len(data.get("reason",""))<10 or not data.get("intervention") or data.get("population") not in self.protocol["population"]["groups"]: raise ValueError("ABSENCE_SCOPE_REQUIRED")
                if not any(e["kind"]=="CALIBRATION_APPROVED" and e["payload"]["basis_hash"]==self.selection_hash(db,events) for e in events): raise ValueError("CALIBRATION_NOT_APPROVED")
                for study in self.catalog(events):
                    state=self.screening(db,study,events)
                    if state["status"] not in {"INCLUIR","EXCLUIR"}: raise ValueError("SCREENING_NOT_COMPLETE")
                    if state["status"]=="INCLUIR" and data["intervention"].casefold() in {v.casefold() for v in state["classification"]["interventions"]} and state["classification"]["population"] in {data["population"],"MISTA_SEM_SEPARACAO"}: raise ValueError("ELIGIBLE_STUDY_EXISTS_NO_RESULT_IS_NOT_ABSENCE")
                data["basis_hash"]=self.selection_hash(db,events)
            else: raise ValueError("UNKNOWN_CLINICAL_ACTION")
            event_id=self.append(db,kind,data,actor)
            return {"event_id":event_id,"action":kind}

    def results(self, db, events):
        adjudications={}; superseded=set()
        for e in events:
            if e["kind"]=="RESULT_ADJUDICATED": adjudications[e["payload"]["result_id"]]=e
        candidates=defaultdict(list)
        for e in events:
            if e["kind"]!="RESULT_DRAFTED": continue
            final=adjudications.get(e["id"])
            if not final or final["payload"]["decision"]!="ACEITAR": continue
            data=e["payload"]
            try: state=self.screening(db,data["study_id"],events)
            except ValueError: continue
            if state["status"]!="INCLUIR" or state["basis_hash"]!=data["basis_hash"]: continue
            try: self.validate_result(db,data,events)
            except ValueError: continue
            reviews=[r for r in events if r["kind"]=="RESULT_REVIEWED" and r["payload"]["result_id"]==e["id"]]
            if not reviews or reviews[-1]["payload"]["decision"]!="ACEITAR" or reviews[-1]["seq"]>final["seq"]: continue
            effect=estimate(data); row={**data,**effect,"outcome_domain":self.protocol["outcomes"][data["outcome_code"]],"result_id":e["id"],"decision_id":final["id"],"design_layer":"OBSERVACIONAL" if data["design"]=="OBSERVACIONAL" else "RCT"}
            key=digest(json_bytes({"study":data["study_id"],"comparison":data["comparison_id"],"scope":scope_for(row)}))
            candidates[key].append(row)
        rows=[]; conflicts=[]
        drafts={e["id"]:e["payload"] for e in events if e["kind"]=="RESULT_DRAFTED"}
        for alternatives in candidates.values():
            for row in alternatives:
                prior=row.get("supersedes")
                while prior:
                    superseded.add(prior); prior=drafts[prior].get("supersedes")
        for key, alternatives in candidates.items():
            alternatives=[r for r in alternatives if r["result_id"] not in superseded]
            if not alternatives: continue
            comparable=[{k:v for k,v in r.items() if k not in {"result_id","decision_id","evidence","supersedes","correction_reason"}} for r in alternatives]
            if len({digest(json_bytes(v)) for v in comparable})>1:
                conflicts.append({"key":key,"result_ids":[r["result_id"] for r in alternatives],"status":"CONFLITO"}); continue
            row=sorted(alternatives,key=lambda r:r["result_id"])[0]
            row["document_result_ids"]=[r["result_id"] for r in alternatives]
            row["document_decision_ids"]=[r["decision_id"] for r in alternatives]
            row["evidence"]=[ref for r in alternatives for ref in r["evidence"]]
            rows.append(row)
        groups=defaultdict(list)
        for row in rows: groups[scope_id(scope_for(row))].append(row)
        output=[]
        current_selection=self.selection_hash(db,events)
        current_calibration=any(e["kind"]=="CALIBRATION_APPROVED" and e["payload"]["basis_hash"]==current_selection for e in events)
        for key, members in groups.items():
            signature=result_set_hash(members)
            judgment=next((e for e in reversed(events) if e["kind"]=="SYNTHESIS_CONCLUDED" and e["payload"].get("selection_hash")==current_selection and e["payload"]["scope"]==scope_for(members[0]) and e["payload"]["result_set_hash"]==signature),None)
            if not current_calibration: judgment=None
            if conflicts: judgment=None
            output.append({"scope_id":key,"scope":scope_for(members[0]),"result_set_hash":signature,"results":members,"study_count":len({r["study_id"] for r in members}),
                "category":judgment["payload"]["category"] if judgment else "REVISAO_DA_SINTESE_PENDENTE","judgment":judgment["payload"] if judgment else None,"judgment_id":judgment["id"] if judgment else None})
        return rows,output,conflicts

    def private_state(self, actor):
        actor.require(*REVIEW_ROLES)
        queue = self.queue(actor)
        with self.transaction() as db:
            events=self.events(db); candidates=[]
            for e in events:
                if e["kind"]=="RESULT_DRAFTED": candidates.append({"id":e["id"],"author":e["actor"],"data":e["payload"]})
            rows,groups,conflicts=self.results(db,events)
            sources=[dict(r) for r in db.execute("SELECT version_id,document_id,content_hash,text_hash,license,access FROM sources ORDER BY document_id,version_id")]
            return {"workspace_id":self.key,"protocol":self.protocol,"queue":queue,"sources":sources,"candidates":candidates,"approved_results":rows,"groups":groups,"conflicts":conflicts}

    def selection_hash(self, db, events):
        return digest(json_bytes({s:{k:v for k,v in self.screening(db,s,events).items() if k!="votes"} for s in self.catalog(events)}))

    def require_current_selection(self,db,events,expected,*,calibrated=False):
        current=self.selection_hash(db,events)
        if expected!=current: raise ValueError("STALE_SELECTION")
        catalog=self.catalog(events)
        if not catalog: raise ValueError("EMPTY_CORPUS")
        if self.unresolved_identity(events):raise ValueError("UNRESOLVED_DOCUMENT_IDENTITY")
        if any(self.screening(db,s,events)["status"] not in {"INCLUIR","EXCLUIR"} for s in catalog): raise ValueError("SCREENING_NOT_COMPLETE")
        if calibrated and not any(e["kind"]=="CALIBRATION_APPROVED" and e["payload"]["basis_hash"]==current for e in events): raise ValueError("CALIBRATION_NOT_APPROVED")
        return current

    def freeze(self):
        with self.transaction() as db:
            events=self.events(db); rows,groups,conflicts=self.results(db,events)
            # Nunca exportar trechos, contatos ou IDs pessoais de revisores.
            public_rows=[]
            for row in rows:
                data={k:v for k,v in row.items() if k not in {"evidence","supersedes","correction_reason"}}
                data["references"]=[]
                for ref in row["evidence"]:
                    source=db.execute("SELECT document_id,content_hash FROM sources WHERE version_id=?",(ref["version_id"],)).fetchone()
                    data["references"].append({**{k:v for k,v in ref.items() if k!="quote"},**dict(source)})
                public_rows.append(data)
            public_groups=[{k:v for k,v in group.items() if k!="results"} | {"result_ids":[r["result_id"] for r in group["results"]],"study_ids":sorted({r["study_id"] for r in group["results"]})} for group in groups]
            screening=[]
            for study in self.catalog(events):
                state=self.screening(db,study,events)
                screening.append({"study_id":study,"basis_hash":state["basis_hash"],"status":state["status"],"classification":state["classification"]})
            basis=self.selection_hash(db,events)
            absences=[e["payload"] | {"decision_id":e["id"],"category":"AUSENCIA_ESTUDO_ELEGIVEL_NO_CORPUS"} for e in events if e["kind"]=="ABSENCE_CONCLUDED" and e["payload"]["basis_hash"]==basis]
            from .integrity import public_notices
            notices=public_notices(events,self.assignments(events)[0])
            return {"schema_version":"clinical-evidence-1","workspace_id":self.key,"protocol":self.protocol,"protocol_hash":digest(json_bytes(self.protocol)),"audit_head":events[-1]["event_hash"] if events else "0"*64,
                **({"document_integrity":notices} if notices else {}),
                "screening":screening,"results":public_rows,"groups":public_groups,"conflicts":conflicts,"absences":absences}

    def snapshot(self):
        data=dict(self.input.data); data["clinical"]=self.freeze()
        return load_snapshot(json_bytes(data),origin={"type":"clinical_workspace","workspace_id":self.key,"base_input_hash":self.input.input_hash})
