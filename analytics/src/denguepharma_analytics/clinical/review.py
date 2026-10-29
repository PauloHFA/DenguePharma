"""Material de revisao independente, importacao atomica e localizadores privados."""
from collections import Counter
import csv
from io import BytesIO, StringIO
import json
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED

from pydantic import Field
from ..domain import digest,json_bytes
from .models import Classification,Screen,Result,EvidenceRef,Strict
from .workspace import REVIEW_ROLES

CLASS_FIELDS=[key for key in Classification.model_fields if key!="interventions"]
META_COLUMNS=["workspace_id","input_hash","protocol_hash","study_id","basis_hash","title","document_ids_json"]
HUMAN_COLUMNS=["decision",*CLASS_FIELDS,"interventions_json","reason"]
COLUMNS=META_COLUMNS+HUMAN_COLUMNS
MAX_BYTES=1024*1024
MAX_REVIEWS=100


def csv_bytes(rows,columns):
    stream=StringIO(newline=""); writer=csv.DictWriter(stream,fieldnames=columns,lineterminator="\n");writer.writeheader()
    def safe(value): return "'"+value if isinstance(value,str) and value.startswith(("=","+","-","@","\t","\r")) else value
    for row in rows:
        writer.writerow({key:safe(row.get(key,"")) for key in columns})
    return stream.getvalue().encode("utf-8")


def progress(workspace,actor):
    from .personal_review import assignment,summary as personal_summary
    actor.require(*REVIEW_ROLES)
    with workspace.transaction() as db:
        events=workspace.events(db); catalog=workspace.catalog(events)
        states=[workspace.screening(db,study,events) for study in catalog]
        personal=personal_summary([assignment(actor.id,study,state,events) for study,state in zip(catalog,states)])
        counts=Counter(s["status"] for s in states)
        missing=sum(max(0,2-len(s["votes"])) for s in states)
        rows,groups,conflicts=workspace.results(db,events)
        selection_hash=workspace.selection_hash(db,events)
        approved=any(e["kind"]=="CALIBRATION_APPROVED" and e["payload"]["basis_hash"]==selection_hash for e in events)
        resolved=bool(states) and all(s["status"] in {"INCLUIR","EXCLUIR"} for s in states)
        identity_pending=len(workspace.unresolved_identity(events))
        return dict(workspace_id=workspace.key,studies=len(states),documents=len(workspace.input.data["documents"]),screening_counts=dict(counts),
            my_review=personal,
            missing_independent_votes=missing,unresolved_studies=sum(s["status"] not in {"INCLUIR","EXCLUIR"} for s in states),
            selection_complete=resolved,unresolved_identity_documents=identity_pending,calibration_approved=approved,approved_results=len(rows),extraction_conflicts=len(conflicts),
            pending_syntheses=sum(g["category"]=="REVISAO_DA_SINTESE_PENDENTE" for g in groups),
            next_step="CONFERIR_IDENTIDADE" if identity_pending else "REVISAR_PILOTO" if not resolved else "DOCUMENTAR_CALIBRACAO" if not approved else "PLANEJAR_COLETA_FINAL",
            notice="Contagem operacional. Dois votos incertos não concluem seleção; seleção completa não aprova calibração automaticamente.")


def package(workspace,actor):
    actor.require(*REVIEW_ROLES)
    with workspace.transaction() as db:
        events=workspace.events(db); catalog=workspace.catalog(events); rows=[]; sources=[]
        protocol_hash=digest(json_bytes(workspace.protocol))
        for study,documents in sorted(catalog.items()):
            rows.append(dict(workspace_id=workspace.key,input_hash=workspace.input.input_hash,protocol_hash=protocol_hash,study_id=study,
                basis_hash=workspace.basis(db,study,events),title=documents[0].get("title") or "",document_ids_json=json.dumps(sorted(d["documentId"] for d in documents))))
        for row in db.execute("SELECT document_id,version_id,content_hash,text_hash,license,access FROM sources ORDER BY document_id,version_id"):
            sources.append(dict(row))
        # Nenhum voto, classificacao, justificativa, ator ou trecho documental e exportado.
        files={"screening_template.csv":csv_bytes(rows,COLUMNS),"sources.csv":csv_bytes(sources,["document_id","version_id","content_hash","text_hash","license","access"]),
            "protocol.json":json_bytes(workspace.protocol),"classification_schema.json":json_bytes(Classification.model_json_schema()),"result_schema.json":json_bytes(Result.model_json_schema()),
            "README.md":("# Pacote privado de revisão independente\n\n"
                "Preencha somente suas próprias decisões em screening_template.csv. Os campos humanos estão vazios intencionalmente.\n"
                "Use valores do classification_schema.json; interventions_json é uma lista JSON, como [\"nome\"], ou [] quando não informada.\n"
                "Não altere workspace_id, input_hash, protocol_hash, study_id ou basis_hash. Não use este CSV como evidência de aprovação.\n"
                "Linhas inteiramente não preenchidas serão ignoradas. Preenchimento parcial, hash antigo ou classificação inválida recusam o lote inteiro.\n"
                "Importe autenticado com sua conta. A identidade vem da sessão; não inclua nomes, senhas, tokens ou papéis na planilha.\n"
                "Não há texto integral nem resumo no pacote. Consulte somente fontes permitidas na área privada.\n"
                "Fontes/catálogos alterados exigem novo pacote. Aprovação de calibração e adjudicação continuam separadas.\n").encode("utf-8")}
        manifest=dict(schema_version="independent-review-package-1",workspace_id=workspace.key,input_hash=workspace.input.input_hash,protocol_hash=protocol_hash,
            studies=len(rows),audit_head=events[-1]["event_hash"] if events else "0"*64,artifacts={name:digest(data) for name,data in files.items()})
        files["manifest.json"]=json_bytes(manifest)
    stream=BytesIO()
    with ZipFile(stream,"w") as archive:
        for name,data in sorted(files.items()):
            info=ZipInfo(name,date_time=(1980,1,1,0,0,0));info.compress_type=ZIP_DEFLATED;info.external_attr=0o600<<16
            archive.writestr(info,data)
    return stream.getvalue()


def parse(content):
    if len(content)>MAX_BYTES: raise ValueError("REVIEW_CSV_TOO_LARGE")
    try: stream=StringIO(content.decode("utf-8-sig"),newline="")
    except UnicodeDecodeError: raise ValueError("REVIEW_CSV_UTF8_REQUIRED") from None
    reader=csv.DictReader(stream)
    if reader.fieldnames!=COLUMNS: raise ValueError("REVIEW_CSV_HEADERS_MUST_MATCH_TEMPLATE")
    records=[]; skipped=0; study_ids=set()
    try:
        for number,row in enumerate(reader,start=2):
            if number>10002: raise ValueError("REVIEW_CSV_TOO_MANY_ROWS")
            if None in row or any(v is None for v in row.values()): raise ValueError("REVIEW_CSV_MALFORMED_ROW")
            if not any(row[key].strip() for key in HUMAN_COLUMNS): skipped+=1;continue
            if row["study_id"] in study_ids: raise ValueError("REVIEW_CSV_DUPLICATE_STUDY")
            study_ids.add(row["study_id"])
            try:
                interventions=json.loads(row["interventions_json"])
                record=Screen.model_validate(dict(study_id=row["study_id"],basis_hash=row["basis_hash"],decision=row["decision"],
                    classification={**{key:row[key] for key in CLASS_FIELDS},"interventions":interventions},reason=row["reason"])).model_dump()
            except (ValueError,TypeError): raise ValueError(f"REVIEW_CSV_INVALID_HUMAN_FIELDS_LINE:{number}") from None
            records.append((row,record))
            if len(records)>MAX_REVIEWS: raise ValueError("REVIEW_CSV_MAX_100_DECISIONS")
    except csv.Error: raise ValueError("REVIEW_CSV_MALFORMED") from None
    if not records: raise ValueError("REVIEW_CSV_NO_COMPLETED_DECISIONS")
    return records,skipped


def _review_csv(workspace,content,actor,*,preview=False,expected_preview=None):
    actor.require(*REVIEW_ROLES)
    records,skipped=parse(content); events_created=[]; unchanged=0; changes=[]
    with workspace.transaction() as db:
        events=workspace.events(db)
        receipt=digest(json_bytes(dict(workspace_id=workspace.key,input_hash=workspace.input.input_hash,
            content_hash=digest(content),actor_id=actor.id,roles=sorted(actor.roles),
            selection_hash=workspace.selection_hash(db,events),
            audit_head=events[-1]["event_hash"] if events else "0"*64)))
        if expected_preview is not None and expected_preview!=receipt:raise ValueError("STALE_REVIEW_PREVIEW")
        for row,record in records:
            if row["workspace_id"]!=workspace.key or row["input_hash"]!=workspace.input.input_hash or row["protocol_hash"]!=digest(json_bytes(workspace.protocol)):
                raise ValueError("REVIEW_CSV_WORKSPACE_OR_PROTOCOL_MISMATCH")
            state=workspace.screening(db,record["study_id"],workspace.events(db))
            if state["basis_hash"]!=record["basis_hash"]: raise ValueError("STALE_REVIEW_BASIS")
            own=state["votes"].get(actor.id)
            operation="UNCHANGED" if own and own["payload"]==record else "UPDATE" if own else "CREATE"
            changes.append(dict(study_id=record["study_id"],operation=operation,decision=record["decision"],classification=record["classification"],reason=record["reason"]))
            if operation=="UNCHANGED":unchanged+=1;continue
            if preview:workspace.validate_screen(db,record,actor,workspace.events(db))
            else:events_created.append(workspace.act("SCREENED",record,actor,transaction=db)["event_id"])
        if preview:
            # Mesma validacao do importador, sem INSERT, IDs ou eventos temporarios.
            return dict(preview=True,receipt=receipt,content_hash=digest(content),
                would_import=sum(r["operation"]!="UNCHANGED" for r in changes),would_create=sum(r["operation"]=="CREATE" for r in changes),
                would_update=sum(r["operation"]=="UPDATE" for r in changes),unchanged=unchanged,skipped=skipped,changes=changes,
                notice="Previa sem gravacao. Somente suas decisoes; nao aprova calibracao nem publica evidencia.")
    return dict(imported=len(events_created),unchanged=unchanged,skipped=skipped,event_ids=events_created)


def preview_csv(workspace,content,actor):
    return _review_csv(workspace,content,actor,preview=True)


def import_csv(workspace,content,actor,*,expected_preview=None):
    return _review_csv(workspace,content,actor,expected_preview=expected_preview)


class LocatorRequest(Strict):
    version_id: str = Field(min_length=1)
    field: str = Field(min_length=1,max_length=128)
    start: int = Field(ge=0)
    end: int = Field(gt=0)


def locator(workspace,request,actor):
    source=workspace.source(request.version_id,actor)
    if request.end<=request.start or request.end>len(source["text"]): raise ValueError("LOCATOR_OUT_OF_BOUNDS")
    ref=EvidenceRef(field=request.field,version_id=request.version_id,text_hash=source["text_hash"],start=request.start,end=request.end,quote=source["text"][request.start:request.end])
    return dict(reference=ref.model_dump(),document_id=source["document_id"],content_hash=source["content_hash"],notice="Localizador literal em texto normalizado; suporte semântico exige revisão humana.")
