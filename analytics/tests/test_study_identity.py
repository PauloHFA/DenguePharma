import copy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from test_clinical import workspace,R1,R2,ADJ,screen,include,complete_calibration,approve,result
from denguepharma_analytics.api import create_app
from denguepharma_analytics.clinical.models import Principal
from denguepharma_analytics.clinical.workspace import create,Workspace
from denguepharma_analytics.clinical.identity import view,preview,confirm,LinkConfirmation
from denguepharma_analytics.clinical.backup import backup,restore
from denguepharma_analytics.clinical.review import progress
from denguepharma_analytics.domain import json_bytes
from denguepharma_analytics.sources.snapshot import load_snapshot


def link(document='t1',study='s1',reason='Synthetic source identity manually checked'):
    return dict(document_id=document,study_id=study,reason=reason)


def send(workspace,data,actor=ADJ):
    prepared=preview(workspace,data,actor)
    return confirm(workspace,LinkConfirmation(link=data,receipt=prepared['receipt']),actor)


def events(workspace):
    with workspace.transaction() as db:return workspace.events(db)


@pytest.mark.requirement('REQ-CLN-013')
def test_identity_does_not_pick_first_ambiguous_legacy_study(workspace,tmp_path):
    data=copy.deepcopy(workspace.input.data)
    data['documents'][0]['studyLinks'].append(dict(study_id='s2',link_certainty='CONFIRMADO'))
    other=create(tmp_path/'ambiguous',load_snapshot(json_bytes(data)),workspace.protocol)
    initial=other.initial_assignments();assert initial['p1']=='p1'
    assert len(other.catalog([]))==3
    row=next(r for r in view(other,R1)['documents'] if r['document_id']=='p1')
    assert row['status']=='AMBIGUIDADE_LEGADA' and row['legacy_study_ids']==['s1','s2']
    data['documents'][0]['studyLinks'].reverse()
    reversed_=create(tmp_path/'reversed',load_snapshot(json_bytes(data)),workspace.protocol)
    assert initial==reversed_.initial_assignments()
    with pytest.raises(ValueError,match='AMBIGUOUS_DOCUMENT_IDENTITY'):screen(other,R1,study='p1')
    with other.transaction() as db:
        with pytest.raises(ValueError,match='UNRESOLVED_DOCUMENT_IDENTITY'):other.require_current_selection(db,[],other.selection_hash(db,[]))
    for study in other.catalog([]):
        screen(other,R1,study=study,decision='EXCLUIR');screen(other,R2,study=study,decision='EXCLUIR')
    assert progress(other,ADJ)['selection_complete'] and progress(other,ADJ)['next_step']=='CONFERIR_IDENTIDADE'
    from denguepharma_analytics.clinical.synthesis import view as synthesis
    assert not synthesis(other,ADJ)['can_approve_calibration']
    with other.transaction() as db:selection_hash=other.selection_hash(db,other.events(db))
    with pytest.raises(ValueError,match='UNRESOLVED_DOCUMENT_IDENTITY'):
        other.act('CALIBRATION_APPROVED',dict(selection_hash=selection_hash,sentinel_ids=['s1'],reason='Synthetic complete screening with unresolved identity'),ADJ)
    send(other,link('p1','s1'))
    assert len(other.catalog(events(other)))==2
    send(reversed_,link('p1','p1',reason='Reviewed ambiguous document remains a separate identity'))
    assert not reversed_.unresolved_identity(events(reversed_))
    assert len(reversed_.catalog(events(reversed_)))==3


@pytest.mark.requirement('REQ-CLN-013')
def test_identity_preview_is_readonly_and_has_no_screening_votes(workspace):
    include(workspace);before=workspace.snapshot().input_hash;history=events(workspace)
    prepared=preview(workspace,link(),ADJ)
    assert prepared['studies_before']==2 and prepared['studies_after']==1
    assert prepared['documents_before']==prepared['documents_after']==3
    assert prepared['impacts'][0]['current_votes_to_recheck']==2
    assert 'classification' not in str(prepared) and R1.id not in str(prepared)
    assert events(workspace)==history and workspace.snapshot().input_hash==before
    with pytest.raises(PermissionError):preview(workspace,link(),R1)
    for invalid,error in [(link('missing'),'INVALID_DOCUMENT'),(link(study='foreign'),'UNKNOWN_STUDY'),(link(study='s2'),'NO_IDENTITY_CHANGE')]:
        with pytest.raises(ValueError,match=error):preview(workspace,invalid,ADJ)
    assert events(workspace)==history


@pytest.mark.requirement('REQ-CLN-013')
def test_identity_correction_never_reactivates_old_reviews_or_calibration(workspace):
    include(workspace);complete_calibration(workspace);approve(workspace,result(workspace))
    frozen=workspace.freeze();assert len(frozen['results'])==1
    source_bytes=workspace.input.content
    send(workspace,link())
    assert len(workspace.catalog(events(workspace)))==1 and not workspace.freeze()['results']
    assert not progress(workspace,ADJ)['calibration_approved']
    send(workspace,link(study='s2',reason='Synthetic corrected identity after independent source check'))
    state=workspace.freeze()
    assert len(state['screening'])==2 and all(s['status']=='PENDENTE' for s in state['screening'])
    assert progress(workspace,ADJ)['missing_independent_votes']==4
    assert not state['results'] and not progress(workspace,ADJ)['calibration_approved']
    assert len(events(workspace))==10 and len(frozen['results'])==1
    assert workspace.input.content==source_bytes


@pytest.mark.requirement('REQ-CLN-013')
def test_identity_confirmation_rejects_stale_actor_payload_audit_and_sources(workspace):
    payload=link();prepared=preview(workspace,payload,ADJ)
    request=LinkConfirmation(link=payload,receipt=prepared['receipt'])
    with pytest.raises(ValueError,match='STALE_IDENTITY'):confirm(workspace,request,Principal('other-admin',('ADMINISTRADOR',)))
    with pytest.raises(PermissionError):confirm(workspace,request,R1)
    altered=LinkConfirmation(link=link(reason='Changed source justification'),receipt=prepared['receipt'])
    with pytest.raises(ValueError,match='STALE_IDENTITY'):confirm(workspace,altered,ADJ)
    screen(workspace)
    with pytest.raises(ValueError,match='STALE_IDENTITY'):confirm(workspace,request,ADJ)
    prepared=preview(workspace,payload,ADJ);request=LinkConfirmation(link=payload,receipt=prepared['receipt'])
    workspace.attach_source(workspace.input.data['documents'][0],'Changed permitted source representation')
    with pytest.raises(ValueError,match='STALE_IDENTITY'):confirm(workspace,request,ADJ)
    assert not any(e['kind']=='DOCUMENT_LINKED' for e in events(workspace))


@pytest.mark.requirement('REQ-CLN-013')
def test_identity_history_and_new_bases_survive_backup_restore(workspace,tmp_path):
    send(workspace,link());send(workspace,link(study='s2'))
    saved=backup(workspace,tmp_path/'identity.zip')
    restore(Path(saved['archive']),tmp_path/'restored',saved['archive_hash'])
    other=Workspace(tmp_path/'restored',workspace.key)
    assert other.snapshot().input_hash==workspace.snapshot().input_hash
    assert view(other,ADJ)==view(workspace,ADJ) and len(view(other,ADJ)['history'])==2
    assert view(other,R1)['history']==[] and not view(other,R1)['can_edit']


@pytest.mark.requirement('REQ-CLN-013')
def test_identity_endpoints_are_private_confirmed_and_do_not_publish(workspace,tmp_path):
    actors={'admin':ADJ,'reviewer':R1,'reader':Principal('reader',('LEITOR',))}
    app=TestClient(create_app(tmp_path,authenticate=lambda token:actors[token]))
    prefix=f'/api/clinical/{workspace.key}/identity';headers={'Authorization':'Bearer admin'}
    assert app.get(prefix).status_code==401
    assert app.get(prefix,headers={'Authorization':'Bearer reader'}).status_code==403
    readonly=app.get(prefix,headers={'Authorization':'Bearer reviewer'}).json()
    assert readonly['can_edit'] is False and readonly['history']==[]
    assert app.post(prefix+'/preview',headers={'Authorization':'Bearer reviewer'},json=link()).status_code==403
    assert app.post(prefix+'/preview',headers=headers,json={}).status_code==422
    prepared=app.post(prefix+'/preview',headers=headers,json=link()).json()
    assert events(workspace)==[]
    data=dict(link=link(),receipt=prepared['receipt'])
    assert app.post(prefix+'/confirm',headers=headers,json=data).status_code==200
    assert app.post(prefix+'/confirm',headers=headers,json=data).status_code==409
    assert len(events(workspace))==1 and app.get('/api/public/analyses').json()==[]


def interface(workspace,monkeypatch,actor=ADJ):
    from streamlit.testing.v1 import AppTest
    from denguepharma_analytics import client
    calls=[]
    def private(path,**kwargs):
        calls.append(path)
        if path.endswith('/identity'):return view(workspace,actor)
        if path.endswith('/preview'):return preview(workspace,kwargs['data'],actor)
        return confirm(workspace,LinkConfirmation(**kwargs['data']),actor)
    monkeypatch.setattr(client,'private',private)
    app=AppTest.from_string("from denguepharma_analytics.clinical.identity_ui import render\nrender('workspace','token')",default_timeout=30).run()
    return app,calls


@pytest.mark.requirement('REQ-CLN-013')
def test_identity_form_requires_explicit_preview_and_confirmation(workspace,monkeypatch):
    app,calls=interface(workspace,monkeypatch)
    assert not app.exception and app.button[0].disabled and len(app.button)==1
    app.selectbox[0].select('t1').run();app.selectbox[1].select('s1')
    app.text_area[0].set_value('Synthetic source linkage verified manually').run()
    app.button[0].click().run()
    assert not app.exception and len(app.button)==2 and events(workspace)==[]
    app.button[1].click().run()
    assert app.error and events(workspace)==[]
    app.checkbox[0].check();app.button[1].click().run()
    assert not app.exception and app.success and len(events(workspace))==1
    assert len([c for c in calls if c.endswith('/confirm')])==1


@pytest.mark.requirement('REQ-CLN-013')
def test_identity_form_clears_changed_preview_and_hides_edit_for_reviewer(workspace,monkeypatch):
    app,_=interface(workspace,monkeypatch)
    app.selectbox[0].select('t1').run();app.selectbox[1].select('s1')
    app.text_area[0].set_value('Synthetic source linkage checked').run();app.button[0].click().run()
    assert len(app.button)==2
    app.text_area[0].set_value('Another independent check of identity').run()
    assert app.warning and len(app.button)==1 and events(workspace)==[]
    other,_=interface(workspace,monkeypatch,R1)
    assert not other.exception and not other.button and not other.selectbox
