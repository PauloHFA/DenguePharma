"""Identidade documental conferida por pessoas; sem fusao ou elegibilidade automaticas."""
from pydantic import Field
from ..domain import digest,json_bytes
from ..identity.identifiers import document_identifiers
from .models import DocumentLink,Strict
from .workspace import REVIEW_ROLES,ADJUDICATORS


class LinkConfirmation(Strict):
    link: DocumentLink
    receipt: str = Field(pattern=r"^[a-f0-9]{64}$")


def view(workspace,actor):
    actor.require(*REVIEW_ROLES)
    with workspace.transaction() as db:
        events=workspace.events(db);assignments,_=workspace.assignments(events);catalog=workspace.catalog(events)
        can_edit=bool(set(actor.roles).intersection(ADJUDICATORS));rows=[]
        linked={e["payload"]["document_id"] for e in events if e["kind"]=="DOCUMENT_LINKED"};unresolved=set(workspace.unresolved_identity(events))
        for doc in workspace.input.data["documents"]:
            confirmed=sorted({str(l["study_id"]) for l in doc.get("studyLinks",[]) if l.get("link_certainty")=="CONFIRMADO"})
            rows.append(dict(document_id=doc["documentId"],title=doc.get("title"),source=doc.get("source"),version_id=doc["versionId"],content_hash=doc["contentHash"],
                identifiers=document_identifiers(doc),study_id=assignments[doc["documentId"]],legacy_study_ids=confirmed,needs_identity_review=doc["documentId"] in unresolved,
                status="VINCULO_HUMANO_REGISTRADO" if doc["documentId"] in linked else "AMBIGUIDADE_LEGADA" if len(confirmed)>1 else "REFERENCIA_INICIAL"))
        return dict(workspace_id=workspace.key,can_edit=can_edit,documents=rows,
            studies=[dict(study_id=s,document_count=len(catalog.get(s,[]))) for s in sorted(workspace.known_study_ids(events))],
            history=[dict(event_id=e["id"],**e["payload"]) for e in events if e["kind"]=="DOCUMENT_LINKED"] if can_edit else [],
            notice="Identificadores e vinculos legados sao referencias para conferencia. Agrupamento documental nao aprova elegibilidade nem resultado clinico.")


def _preview(workspace,payload,actor,db):
    events=workspace.events(db);data=workspace.validate_document_link(payload,actor,events)
    assignments,_=workspace.assignments(events);previous=assignments[data["document_id"]]
    catalog=workspace.catalog(events);after=dict(assignments);after[data["document_id"]]=data["study_id"]
    impacts=[]
    for study in sorted({previous,data["study_id"]}):
        documents=sorted(d for d,s in after.items() if s==study)
        state=workspace.screening(db,study,events) if study in catalog else None
        impacts.append(dict(study_id=study,before_documents=sorted(d["documentId"] for d in catalog.get(study,[])),after_documents=documents,
            current_votes_to_recheck=len(state["votes"]) if state else 0,remains_in_catalog=bool(documents)))
    receipt=digest(json_bytes(dict(workspace_id=workspace.key,input_hash=workspace.input.input_hash,link=data,actor_id=actor.id,roles=sorted(actor.roles),
        selection_hash=workspace.selection_hash(db,events),audit_head=events[-1]["event_hash"] if events else "0"*64)))
    return dict(link=data,receipt=receipt,from_study=previous,to_study=data["study_id"],impacts=impacts,
        studies_before=len(catalog),studies_after=len(set(after.values())),documents_before=len(assignments),documents_after=len(after),
        published=False,notice="Previa sem gravacao. Confirmar muda a base dos estudos afetados; votos e resultados antigos exigem nova revisao, inclusive ao desfazer o vinculo. Fontes e snapshots historicos sao preservados.")


def preview(workspace,payload,actor):
    actor.require(*ADJUDICATORS)
    with workspace.transaction() as db:return _preview(workspace,payload,actor,db)


def confirm(workspace,request,actor):
    actor.require(*ADJUDICATORS)
    with workspace.transaction() as db:
        current=_preview(workspace,request.link.model_dump(),actor,db)
        if current["receipt"]!=request.receipt:raise ValueError("STALE_IDENTITY_PREVIEW")
        return workspace.act("DOCUMENT_LINKED",current["link"],actor,transaction=db)
