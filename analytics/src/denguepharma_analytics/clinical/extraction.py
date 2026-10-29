"""Previa e fluxo de extracao sem publicar nem interpretar eficacia."""
from .effects import estimate
from .workspace import REVIEW_ROLES,ADJUDICATORS


def preview(workspace,payload,actor):
    actor.require(*REVIEW_ROLES)
    with workspace.transaction() as db:
        events=workspace.events(db); data=workspace.validate_result(db,payload,events)
        try:
            workspace.validate_evidence(db,data,events); support=dict(complete=True,code="LITERAL_REFERENCES_VALID")
        except ValueError as error: support=dict(complete=False,code=str(error))
        return dict(effect=estimate(data),support=support,published=False,
            notice="Prévia por estudo. Suporte literal não comprova interpretação semântica; revisão independente e adjudicação continuam necessárias.")


def workflow(workspace,actor):
    actor.require(*REVIEW_ROLES)
    with workspace.transaction() as db:
        events=workspace.events(db); catalog=workspace.catalog(events); included=[]
        states={study:workspace.screening(db,study,events) for study in catalog}
        for study,state in states.items():
            if state["status"]=="INCLUIR":
                included.append(dict(study_id=study,basis_hash=state["basis_hash"],title=catalog[study][0].get("title"),
                    document_ids=[d["documentId"] for d in catalog[study]],classification=state["classification"]))
        rows,_,conflicts=workspace.results(db,events)
        approved={i for r in rows for i in r["document_result_ids"]}
        conflicting={i for c in conflicts for i in c["result_ids"]}; cards=[]
        superseded={}
        drafts={e["id"]:e["payload"] for e in events if e["kind"]=="RESULT_DRAFTED"}
        for candidate in approved:
            prior=drafts[candidate].get("supersedes")
            while prior:
                superseded[prior]=candidate;prior=drafts[prior].get("supersedes")
        for event in events:
            if event["kind"]!="RESULT_DRAFTED": continue
            data=event["payload"]; state=states.get(data["study_id"])
            current=bool(state and state["status"]=="INCLUIR" and state["basis_hash"]==data["basis_hash"])
            if current:
                try: workspace.validate_result(db,data,events)
                except ValueError: current=False
            reviews=[e for e in events if e["kind"]=="RESULT_REVIEWED" and e["payload"]["result_id"]==event["id"]]
            finals=[e for e in events if e["kind"]=="RESULT_ADJUDICATED" and e["payload"]["result_id"]==event["id"]]
            last_review=reviews[-1] if reviews else None; final=finals[-1] if finals else None
            stage="AGUARDA_REVISAO"
            if last_review: stage="AGUARDA_ADJUDICACAO" if last_review["payload"]["decision"]=="ACEITAR" else "REVISAO_REJEITADA"
            if final: stage="REAVALIACAO_PENDENTE" if final["payload"]["decision"]=="ACEITAR" else "ADJUDICACAO_REJEITADA"
            if event["id"] in approved: stage="APROVADO"
            if event["id"] in superseded: stage="SUBSTITUIDO"
            if event["id"] in conflicting: stage="CONFLITO"
            if not current: stage="BASE_DESATUALIZADA"
            can_review=current and actor.id!=event["actor"] and event["id"] not in superseded
            can_adjudicate=can_review and bool(set(actor.roles).intersection(ADJUDICATORS)) and bool(last_review and last_review["payload"]["decision"]=="ACEITAR") and actor.id not in {e["actor"] for e in reviews}
            cards.append(dict(id=event["id"],author=event["actor"],data=data,stage=stage,can_review=can_review,can_adjudicate=can_adjudicate,
                latest_review=last_review["payload"] if last_review else None,latest_adjudication=final["payload"] if final else None,
                effect=estimate(data),replaced_by=superseded.get(event["id"])))
        return dict(workspace_id=workspace.key,included_studies=included,candidates=cards,conflicts=conflicts,outcomes=workspace.protocol["outcomes"])
