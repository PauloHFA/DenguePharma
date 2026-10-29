"""Human documentary alerts; suspend current evidence without rewriting history."""
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field,model_validator
from ..domain import digest,json_bytes
from .models import Strict
from .workspace import REVIEW_ROLES,ADJUDICATORS

EVENT='DOCUMENT_INTEGRITY_RECORDED'
BLOCKED={'EM_REAVALIACAO','RETIRADO'}


class IntegrityNotice(Strict):
    document_id: str
    status: Literal['EM_REAVALIACAO','RETIRADO','REGULARIZADO']
    category: Literal['RETRATACAO','CORRECAO_RELEVANTE','OUTRO_ALERTA_DOCUMENTAL']
    source_reference: str = Field(min_length=8)
    reason: str = Field(min_length=10)

    @model_validator(mode='after')
    def reference(self):
        parsed=urlsplit(self.source_reference)
        if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or any(c.isspace() for c in self.source_reference):
            raise ValueError('HTTPS_REFERENCE_REQUIRED')
        return self


class IntegrityConfirmation(Strict):
    notice: IntegrityNotice
    receipt: str = Field(pattern=r'^[a-f0-9]{64}$')


def latest(events):
    return {e['payload']['document_id']:e for e in events if e['kind']==EVENT}


def blocked_documents(events):
    return {document:event['payload']['status'] for document,event in latest(events).items() if event['payload']['status'] in BLOCKED}


def revisions(events,document_ids):
    return [e['id'] for e in events if e['kind']==EVENT and e['payload']['document_id'] in document_ids]


def public_notices(events,assignments):
    return [dict(event_id=e['id'],study_id=assignments[document],**{k:e['payload'][k] for k in
        ('document_id','version_id','content_hash','status','category','source_reference')})
        for document,e in sorted(latest(events).items())]


def view(workspace,actor):
    actor.require(*REVIEW_ROLES)
    with workspace.transaction() as db:
        events=workspace.events(db);current=latest(events);assignments,_=workspace.assignments(events)
        rows=[]
        for document in workspace.input.data['documents']:
            event=current.get(document['documentId'])
            rows.append(dict(document_id=document['documentId'],title=document.get('title'),study_id=assignments[document['documentId']],
                version_id=document['versionId'],content_hash=document['contentHash'],
                status=event['payload']['status'] if event else 'SEM_ALERTA_REGISTRADO',
                notice=event['payload'] if event else None))
        return dict(workspace_id=workspace.key,can_edit=bool(set(actor.roles).intersection(ADJUDICATORS)),documents=rows,
            blocked_documents=len(blocked_documents(events)),
            history=[dict(event_id=e['id'],**e['payload']) for e in events if e['kind']==EVENT] if set(actor.roles).intersection(ADJUDICATORS) else [],
            notice='Alertas documentais humanos, sem detecção automática de retratações. Ausência de alerta não certifica a integridade da literatura. '
                'Suspender exige nova revisão da base; regularizar não reativa aprovações antigas. Publicações históricas permanecem imutáveis.')


def _preview(workspace,payload,actor,db):
    actor.require(*ADJUDICATORS)
    notice=IntegrityNotice.model_validate(payload).model_dump();events=workspace.events(db)
    documents={d['documentId']:d for d in workspace.input.data['documents']}
    document=documents.get(notice['document_id'])
    if not document:raise ValueError('UNKNOWN_INTEGRITY_DOCUMENT')
    current=latest(events).get(notice['document_id'])
    if notice['status']=='REGULARIZADO' and (not current or current['payload']['status'] not in BLOCKED):
        raise ValueError('ACTIVE_ALERT_REQUIRED')
    if current and all(current['payload'][k]==v for k,v in notice.items()):raise ValueError('NO_INTEGRITY_CHANGE')
    assignments,_=workspace.assignments(events);study=assignments[notice['document_id']]
    state=workspace.screening(db,study,events);rows,groups,_=workspace.results(db,events)
    affected=[r for r in rows if r['study_id']==study]
    data=dict(**notice,version_id=document['versionId'],content_hash=document['contentHash'])
    selection=workspace.selection_hash(db,events)
    receipt=digest(json_bytes(dict(workspace_id=workspace.key,input_hash=workspace.input.input_hash,notice=data,
        actor_id=actor.id,roles=sorted(actor.roles),selection_hash=selection,
        audit_head=events[-1]['event_hash'] if events else '0'*64)))
    return dict(notice=notice,receipt=receipt,study_id=study,document_id=notice['document_id'],
        previous_status=current['payload']['status'] if current else 'SEM_ALERTA_REGISTRADO',
        current_votes_to_recheck=len(state['votes']),approved_results_to_recheck=len(affected),
        synthesis_groups_to_recheck=sum(any(r['study_id']==study for r in g['results']) for g in groups),
        calibration_to_recheck=any(e['kind']=='CALIBRATION_APPROVED' and e['payload']['basis_hash']==selection for e in events),
        published=False,warning='Prévia sem gravação. Confirmar muda a base do estudo atual do documento, invalida revisões anteriores '
            'e preserva fontes, eventos e snapshots. Não atualiza ou retira automaticamente execuções públicas históricas.')


def preview(workspace,payload,actor):
    actor.require(*ADJUDICATORS)
    with workspace.transaction() as db:return _preview(workspace,payload,actor,db)


def confirm(workspace,request,actor):
    actor.require(*ADJUDICATORS)
    with workspace.transaction() as db:
        prepared=_preview(workspace,request.notice.model_dump(),actor,db)
        if prepared['receipt']!=request.receipt:raise ValueError('STALE_INTEGRITY_PREVIEW')
        document=next(d for d in workspace.input.data['documents'] if d['documentId']==request.notice.document_id)
        data=dict(**prepared['notice'],version_id=document['versionId'],content_hash=document['contentHash'])
        event_id=workspace.append(db,EVENT,data,actor)
        return dict(event_id=event_id,action=EVENT)
