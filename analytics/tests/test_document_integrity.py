import copy
import json

import pytest
from fastapi.testclient import TestClient
from test_clinical import workspace,R1,R2,ADJ,include,screen,result,approve,complete_calibration
from denguepharma_analytics.api import create_app
from denguepharma_analytics.clinical.models import Principal
from denguepharma_analytics.clinical.integrity import view,preview,confirm,IntegrityConfirmation
from denguepharma_analytics.clinical.review import progress
from denguepharma_analytics.clinical.dossier import view as dossier
from denguepharma_analytics.storage import export,publish,require_published,public_summary


def notice(**changes):
    return dict(document_id='p1',status='RETIRADO',category='RETRATACAO',
        source_reference='https://example.org/synthetic-notice',
        reason='Synthetic documentary notice checked manually',**changes)


def send(workspace,payload):
    prepared=preview(workspace,payload,ADJ)
    return confirm(workspace,IntegrityConfirmation(notice=payload,receipt=prepared['receipt']),ADJ)


def history(workspace):
    with workspace.transaction() as db:return workspace.events(db)


def approved(workspace):
    include(workspace);complete_calibration(workspace)
    payload=result(workspace);candidate=approve(workspace,payload)
    return candidate,payload


@pytest.mark.requirement('REQ-CLN-003')
def test_integrity_preview_is_readonly_and_quantifies_current_impact(workspace):
    candidate,_=approved(workspace)
    before=history(workspace);snapshot=workspace.snapshot().input_hash
    prepared=preview(workspace,notice(),ADJ)
    assert prepared['current_votes_to_recheck']==2 and prepared['approved_results_to_recheck']==1
    assert prepared['synthesis_groups_to_recheck']==1 and prepared['calibration_to_recheck']
    assert prepared['published'] is False
    assert R1.id not in json.dumps(prepared) and R2.id not in json.dumps(prepared)
    assert history(workspace)==before and workspace.snapshot().input_hash==snapshot
    assert workspace.freeze()['results'][0]['result_id']==candidate


@pytest.mark.requirement('REQ-CLN-003')
def test_integrity_withdrawal_removes_current_results_but_preserves_history(workspace):
    candidate,payload=approved(workspace)
    old=copy.deepcopy(workspace.freeze());original=workspace.input.content
    old_sources=workspace.private_state(R1)['sources'];events=history(workspace)
    send(workspace,notice())
    current=workspace.freeze()
    assert current['results']==[] and current['groups']==[]
    assert len(history(workspace))==len(events)+1 and old['results'][0]['result_id']==candidate
    assert workspace.input.content==original and workspace.private_state(R1)['sources']==old_sources
    assert progress(workspace,R1)['missing_independent_votes']==2
    assert not progress(workspace,R1)['calibration_approved']
    assert dossier(workspace,'s1',R1)['integrity_alerts']=={'p1':'RETIRADO'}
    with pytest.raises(ValueError,match='DOCUMENT_INTEGRITY_REVIEW_REQUIRED'):screen(workspace,R1)
    with pytest.raises(ValueError,match='DOCUMENT_INTEGRITY_REVIEW_REQUIRED'):
        workspace.act('RESULT_DRAFTED',payload,R1)
    exported=current['document_integrity'][0]
    assert exported['status']=='RETIRADO' and exported['content_hash']==workspace.input.data['documents'][0]['contentHash']
    assert 'reason' not in exported and 'actor' not in exported
    assert workspace.source(old_sources[0]['version_id'],R1)['text']


@pytest.mark.requirement('REQ-CLN-003')
def test_integrity_regularization_never_reactivates_old_approvals(workspace):
    _,payload=approved(workspace);old_basis=payload['basis_hash']
    send(workspace,notice())
    send(workspace,{**notice(),'status':'REGULARIZADO','reason':'Synthetic corrected notice manually verified'})
    assert view(workspace,R1)['blocked_documents']==0
    assert workspace.freeze()['results']==[] and not progress(workspace,R1)['calibration_approved']
    row=next(r for r in workspace.queue(R1) if r['study_id']=='s1')
    assert row['basis_hash']!=old_basis and row['own_decision'] is None
    include(workspace)
    assert not workspace.freeze()['results']
    with pytest.raises(ValueError,match='INCLUDED_CURRENT_STUDY_REQUIRED'):
        workspace.act('RESULT_DRAFTED',payload,R1)
    fresh={**payload,'basis_hash':next(r for r in workspace.queue(R1) if r['study_id']=='s1')['basis_hash']}
    approve(workspace,fresh)
    assert len(workspace.freeze()['results'])==1
    assert len([e for e in history(workspace) if e['kind']=='DOCUMENT_INTEGRITY_RECORDED'])==2


@pytest.mark.requirement('REQ-CLN-003')
def test_integrity_receipt_is_bound_to_actor_payload_sources_and_audit(workspace):
    data=notice();prepared=preview(workspace,data,ADJ)
    request=IntegrityConfirmation(notice=data,receipt=prepared['receipt'])
    other=Principal('another-synthetic-admin',('ADMINISTRADOR',))
    with pytest.raises(ValueError,match='STALE_INTEGRITY_PREVIEW'):confirm(workspace,request,other)
    with pytest.raises(ValueError,match='STALE_INTEGRITY_PREVIEW'):
        confirm(workspace,IntegrityConfirmation(notice={**data,'reason':'Synthetic modified rationale after preview'},receipt=prepared['receipt']),ADJ)
    workspace.attach_source(workspace.input.data['documents'][0],'Synthetic new permitted source representation')
    with pytest.raises(ValueError,match='STALE_INTEGRITY_PREVIEW'):confirm(workspace,request,ADJ)
    prepared=preview(workspace,data,ADJ)
    screen(workspace,R1,study='s2',decision='EXCLUIR')
    with pytest.raises(ValueError,match='STALE_INTEGRITY_PREVIEW'):
        confirm(workspace,IntegrityConfirmation(notice=data,receipt=prepared['receipt']),ADJ)
    assert not view(workspace,R1)['blocked_documents']


@pytest.mark.requirement('REQ-CLN-003')
def test_integrity_alert_follows_document_when_identity_is_changed(workspace):
    approved(workspace);send(workspace,notice())
    workspace.act('DOCUMENT_LINKED',dict(document_id='p1',study_id='s2',reason='Synthetic corrected documentary identity'),ADJ)
    assert dossier(workspace,'s1',R1)['integrity_alerts']=={}
    assert dossier(workspace,'s2',R1)['integrity_alerts']=={'p1':'RETIRADO'}
    assert not workspace.freeze()['results']
    with pytest.raises(ValueError,match='DOCUMENT_INTEGRITY_REVIEW_REQUIRED'):screen(workspace,R1,study='s2')
    assert view(workspace,ADJ)['blocked_documents']==1


@pytest.mark.requirement('REQ-CLN-003')
def test_integrity_permissions_api_errors_and_confirmation_cannot_be_bypassed(workspace,tmp_path):
    actors={'admin':ADJ,'reviewer':R1,'reader':Principal('reader',('LEITOR',))}
    app=TestClient(create_app(tmp_path,authenticate=lambda token:actors[token]))
    prefix=f'/api/clinical/{workspace.key}';url=prefix+'/integrity'
    assert app.get(url).status_code==401
    assert app.get(url,headers={'Authorization':'Bearer reader'}).status_code==403
    read=app.get(url,headers={'Authorization':'Bearer reviewer'})
    assert read.status_code==200 and read.headers['Cache-Control']=='no-store'
    assert read.json()['can_edit'] is False and read.json()['history']==[]
    assert app.post(url+'/preview',json=notice(),headers={'Authorization':'Bearer reviewer'}).status_code==403
    auth={'Authorization':'Bearer admin'}
    assert app.post(url+'/preview',json={**notice(),'status':'REGULARIZADO'},headers=auth).status_code==409
    assert app.post(url+'/preview',json={**notice(),'document_id':'unknown'},headers=auth).status_code==409
    for reference in ['javascript:invalid','https://','https://user:secret@example.org/notice']:
        assert app.post(url+'/preview',json={**notice(),'source_reference':reference},headers=auth).status_code==422
    assert app.post(prefix+'/actions/DOCUMENT_INTEGRITY_RECORDED',json=notice(),headers=auth).status_code==409
    prepared=app.post(url+'/preview',json=notice(),headers=auth).json()
    assert history(workspace)==[]
    stale=dict(notice=notice(),receipt='0'*64)
    assert app.post(url+'/confirm',json=stale,headers=auth).status_code==409
    response=app.post(url+'/confirm',json=dict(notice=notice(),receipt=prepared['receipt']),headers=auth)
    assert response.status_code==200 and len(history(workspace))==1
    assert app.get(url,headers=auth).json()['blocked_documents']==1
    assert app.post(url+'/preview',json=notice(),headers=auth).status_code==409


@pytest.mark.requirement('REQ-CLN-003')
def test_integrity_new_publication_omits_withdrawn_evidence_and_preserves_old_run(workspace,tmp_path):
    approved(workspace)
    before=export(workspace.snapshot(),tmp_path);publish(tmp_path,before['run_id'])
    assert public_summary(tmp_path,before['run_id'])['clinical']['reviewed_results']==1
    send(workspace,notice())
    after=export(workspace.snapshot(),tmp_path);publish(tmp_path,after['run_id'])
    assert public_summary(tmp_path,after['run_id'])['clinical']['reviewed_results']==0
    assert public_summary(tmp_path,after['run_id'])['clinical']['document_integrity']['blocked_documents']==1
    assert require_published(tmp_path,before['run_id'])==before
    assert public_summary(tmp_path,before['run_id'])['clinical']['reviewed_results']==1


@pytest.mark.requirement('REQ-CLN-003')
def test_integrity_backup_restore_preserves_alert_and_immutable_input(workspace,tmp_path):
    from denguepharma_analytics.clinical.backup import backup,restore
    send(workspace,notice())
    prepared=backup(workspace,tmp_path/'integrity-private.zip')
    restore(tmp_path/'integrity-private.zip',tmp_path/'restored',expected_hash=prepared['archive_hash'])
    from denguepharma_analytics.clinical.workspace import Workspace
    other=Workspace(tmp_path/'restored',workspace.key)
    assert other.input.content==workspace.input.content and other.freeze()==workspace.freeze()
    assert view(other,R1)['blocked_documents']==1


@pytest.mark.requirement('REQ-CLN-003')
def test_integrity_ui_starts_blank_and_requires_explicit_confirmation(workspace,monkeypatch):
    from streamlit.testing.v1 import AppTest
    from denguepharma_analytics import client
    calls=[]
    def private(path,**kwargs):
        if path.endswith('/integrity'):return view(workspace,ADJ)
        if path.endswith('/preview'):return preview(workspace,kwargs['data'],ADJ)
        calls.append(kwargs['data'])
        return confirm(workspace,IntegrityConfirmation.model_validate(kwargs['data']),ADJ)
    monkeypatch.setattr(client,'private',private)
    app=AppTest.from_string("from denguepharma_analytics.clinical.integrity_ui import render\nrender('workspace','private-token')").run()
    assert not app.exception and all(w.value is None for w in app.selectbox)
    assert next(w for w in app.button if w.label=='Conferir impacto do alerta').disabled
    app.selectbox[0].set_value('p1');app.selectbox[1].set_value('EM_REAVALIACAO');app.selectbox[2].set_value('CORRECAO_RELEVANTE')
    app.text_input[0].set_value('https://example.org/synthetic-correction');app.text_area[0].set_value('Synthetic documentary correction checked manually')
    app.run();next(w for w in app.button if w.label=='Conferir impacto do alerta').click().run()
    assert not app.exception and history(workspace)==[]
    next(w for w in app.button if w.label=='Confirmar alteração de integridade').click().run()
    assert app.error and history(workspace)==[]
    app.checkbox[0].check();next(w for w in app.button if w.label=='Confirmar alteração de integridade').click().run()
    assert not app.exception and len(calls)==1 and len(history(workspace))==1


@pytest.mark.requirement('REQ-CLN-003')
def test_integrity_import_rejects_conflicting_or_private_frozen_notices(workspace):
    from denguepharma_analytics.clinical.analysis import validate
    approved(workspace);before=workspace.freeze();send(workspace,notice())
    current=workspace.freeze()
    validate(current)
    forged={**before,'document_integrity':current['document_integrity']}
    with pytest.raises(ValueError,match='BLOCKED_CLINICAL_REFERENCE'):validate(forged)
    for notices in [current['document_integrity']*2,[{**current['document_integrity'][0],'reason':'Private free text'}]]:
        with pytest.raises(ValueError,match='INVALID_INTEGRITY_NOTICE'):validate({**current,'document_integrity':notices})
