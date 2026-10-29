"""Estado da calibracao e dos julgamentos; nenhum rotulo clinico e calculado."""
from .workspace import REVIEW_ROLES,ADJUDICATORS


def view(workspace,actor):
    actor.require(*REVIEW_ROLES)
    with workspace.transaction() as db:
        events=workspace.events(db); catalog=workspace.catalog(events)
        selection_hash=workspace.selection_hash(db,events)
        states={s:workspace.screening(db,s,events) for s in catalog}
        complete=bool(states) and all(s["status"] in {"INCLUIR","EXCLUIR"} for s in states.values())
        identity_pending=bool(workspace.unresolved_identity(events))
        calibration=next((e for e in reversed(events) if e["kind"]=="CALIBRATION_APPROVED" and e["payload"]["basis_hash"]==selection_hash),None)
        can_adjudicate=bool(set(actor.roles).intersection(ADJUDICATORS))
        _,groups,conflicts=workspace.results(db,events)
        blockers=[]
        if not can_adjudicate: blockers.append("PAPEL_DE_ADJUDICADOR_NECESSARIO")
        if not complete: blockers.append("SELECAO_INDEPENDENTE_PENDENTE")
        if identity_pending:blockers.append("IDENTIDADE_DOCUMENTAL_AMBIGUA")
        if not calibration: blockers.append("CALIBRACAO_ATUAL_NAO_APROVADA")
        if conflicts: blockers.append("CONFLITOS_DE_EXTRACAO_PENDENTES")
        cards=[]
        for group in groups:
            benefit_allowed=group["scope"]["design_layer"]=="RCT" and all(r["risk_of_bias"]!="NAO_AVALIADO" for r in group["results"])
            cards.append({**group,"can_conclude":not blockers,"available_categories":["BENEFICIO_SUSTENTADO","EVIDENCIA_INCONCLUSIVA","SINAL_DANO"] if benefit_allowed else ["EVIDENCIA_INCONCLUSIVA","SINAL_DANO"]})
        return dict(workspace_id=workspace.key,selection_hash=selection_hash,selection_complete=complete,can_approve_calibration=can_adjudicate and complete and not identity_pending,
            calibration_approved=bool(calibration),calibration=calibration["payload"] if calibration else None,
            studies=[dict(study_id=s,title=catalog[s][0].get("title"),status=states[s]["status"]) for s in catalog],
            groups=cards,conflicts=conflicts,blockers=blockers,can_conclude_absence=can_adjudicate and complete and not identity_pending and bool(calibration),
            populations=workspace.protocol["population"]["groups"],notice="Categorias exigem julgamento humano por desfecho e contexto; nenhuma decisão publica uma execução automaticamente.")
