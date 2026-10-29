import copy
import json
from urllib.parse import urlsplit,parse_qs,unquote

import pytest
from fastapi.testclient import TestClient
from test_clinical import workspace,R1,R2,ADJ,screen
from denguepharma_analytics.api import create_app
from denguepharma_analytics.clinical.models import Principal
from denguepharma_analytics.clinical.workspace import create
from denguepharma_analytics.clinical.review import progress
from denguepharma_analytics.clinical.personal_review import visible_rows
from denguepharma_analytics.clinical.dossier import view as dossier
from denguepharma_analytics.domain import json_bytes
from denguepharma_analytics.sources.snapshot import load_snapshot


def history(workspace):
    with workspace.transaction() as db:return workspace.events(db)


@pytest.mark.requirement('REQ-CLN-008')
def test_personal_workload_separates_account_tasks_from_global_votes(workspace,tmp_path):
    first=progress(workspace,R1)
    assert first['missing_independent_votes']==4
    assert first['my_review']['available_tasks']==first['my_review']['first_reviews_pending']==2
    screen(workspace,R1)
    mine=progress(workspace,R1)['my_review'];other=progress(workspace,R2)['my_review']
    assert mine['current_registered']==mine['available_tasks']==1
    assert other['current_registered']==0 and other['available_tasks']==2
    assert progress(workspace,R2)['missing_independent_votes']==3
    for state in [mine,other]:
        assert state['total']==sum(state[k] for k in ['current_registered','first_reviews_pending','reassessments_pending','occupied_slots'])
        for forbidden in [R1.id,R2.id,'classification','decision','reason','TEST-DRUG']:
            assert forbidden not in json.dumps(state)
    data=copy.deepcopy(workspace.input.data);data['documents']=[]
    empty=create(tmp_path/'empty',load_snapshot(json_bytes(data)),workspace.protocol)
    assert progress(empty,R1)['my_review']['total']==0
    assert progress(empty,R1)['my_review']['available_tasks']==0
    assert not progress(empty,R1)['selection_complete']


@pytest.mark.requirement('REQ-CLN-008')
def test_personal_registered_uncertain_vote_does_not_resolve_selection(workspace):
    screen(workspace,R1,decision='INCERTO')
    screen(workspace,R2,decision='INCERTO')
    current=progress(workspace,R1)
    assert current['my_review']['current_registered']==1
    assert current['screening_counts']['INCERTO']==1 and not current['selection_complete']
    assert not current['calibration_approved']
    rows=visible_rows(workspace.queue(R1),'Minha revisão registrada')
    assert len(rows)==1 and rows[0]['own_decision']['decision']=='INCERTO'


@pytest.mark.requirement('REQ-CLN-008')
def test_personal_slots_and_adjudication_do_not_create_assignments(workspace):
    screen(workspace,R1)
    screen(workspace,R2,decision='EXCLUIR')
    admin=next(r for r in workspace.queue(ADJ) if r['study_id']=='s1')
    own=next(r for r in workspace.queue(R1) if r['study_id']=='s1')
    assert admin['personal_review']['status']=='VAGAS_OCUPADAS'
    assert not admin['personal_review']['can_review'] and admin['can_adjudicate_screening']
    assert own['personal_review']['can_review'] and not own['can_adjudicate_screening']
    assert len(visible_rows(workspace.queue(ADJ),'Conflitos para adjudicação'))==1
    assert not visible_rows(workspace.queue(R1),'Conflitos para adjudicação')
    assert progress(workspace,ADJ)['my_review']['occupied_slots']==1
    with pytest.raises(ValueError,match='TWO_REVIEWERS_ALREADY_ASSIGNED'):screen(workspace,ADJ)
    assert len(history(workspace))==2


@pytest.mark.requirement('REQ-CLN-008')
def test_personal_source_changes_require_reassessment_without_copying_decisions(workspace):
    screen(workspace,R1)
    old=workspace.queue(R1)[0]['basis_hash']
    workspace.attach_source(workspace.input.data['documents'][0],'Synthetic changed normalized source')
    row=next(r for r in workspace.queue(R1) if r['study_id']=='s1')
    assert row['basis_hash']!=old and row['own_decision'] is None
    assert row['personal_review']==dict(status='REAVALIACAO_NECESSARIA',can_review=True,has_outdated_own_review=True)
    mine=progress(workspace,R1)['my_review']
    assert mine['current_registered']==0 and mine['reassessments_pending']==1 and mine['first_reviews_pending']==1
    assert len(visible_rows(workspace.queue(R1),'Minha revisão pendente'))==2
    screen(workspace,R1)
    assert progress(workspace,R1)['my_review']['reassessments_pending']==0
    assert len(history(workspace))==2


@pytest.mark.requirement('REQ-CLN-008')
def test_personal_identity_changes_never_restore_registered_reviews(workspace):
    screen(workspace,R1);screen(workspace,R1,study='s2')
    assert progress(workspace,R1)['my_review']['current_registered']==2
    workspace.act('DOCUMENT_LINKED',dict(document_id='t1',study_id='s1',reason='Synthetic manually checked identity merge'),ADJ)
    merged=progress(workspace,R1)['my_review']
    assert merged['total']==merged['reassessments_pending']==1 and merged['current_registered']==0
    workspace.act('DOCUMENT_LINKED',dict(document_id='t1',study_id='s2',reason='Synthetic manually corrected identity'),ADJ)
    reverted=progress(workspace,R1)['my_review']
    assert reverted['total']==reverted['reassessments_pending']==2 and reverted['current_registered']==0
    assert not visible_rows(workspace.queue(R1),'Minha revisão registrada')


@pytest.mark.requirement('REQ-CLN-008')
def test_personal_api_is_account_bound_and_private_without_mutation(workspace,tmp_path):
    screen(workspace,R1)
    actors={'one':R1,'two':R2,'reader':Principal('reader',('LEITOR',))}
    app=TestClient(create_app(tmp_path,authenticate=lambda token:actors[token]))
    prefix=f'/api/clinical/{workspace.key}'
    before=history(workspace)
    for endpoint in ['/progress','/state']:
        assert app.get(prefix+endpoint).status_code==401
        assert app.get(prefix+endpoint,headers={'Authorization':'Bearer reader'}).status_code==403
        response=app.get(prefix+endpoint,headers={'Authorization':'Bearer one'})
        assert response.status_code==200 and response.headers['Cache-Control']=='no-store'
    one=app.get(prefix+'/progress',headers={'Authorization':'Bearer one'}).json()['my_review']
    two=app.get(prefix+'/progress',headers={'Authorization':'Bearer two'}).json()['my_review']
    assert one['current_registered']==1 and two['current_registered']==0
    assert history(workspace)==before


def ui_client(workspace,actor,monkeypatch):
    from denguepharma_analytics import client
    writes=[]
    def private(path,**kwargs):
        if path.endswith('/state'):return workspace.private_state(actor)
        if '/dossier?' in path:
            parsed=urlsplit(path);study=unquote(parsed.path.split('/')[-2])
            return dossier(workspace,study,actor,expected_basis=parse_qs(parsed.query)['basis_hash'][0])
        kind=path.rsplit('/',1)[-1]
        writes.append(kwargs['data'])
        return workspace.act(kind,kwargs['data'],actor)
    monkeypatch.setattr(client,'private',private)
    return writes


def ui_script():
    return "from denguepharma_analytics import client\nfrom denguepharma_analytics.clinical.screening_ui import render\nrender(client.private('/workspace/state'),'workspace','private-token')"


@pytest.mark.requirement('REQ-CLN-008')
def test_personal_ui_filters_only_own_work_without_writing(workspace,monkeypatch):
    from streamlit.testing.v1 import AppTest
    screen(workspace,R1)
    before=history(workspace);writes=ui_client(workspace,R1,monkeypatch)
    app=AppTest.from_string(ui_script()).run()
    assert not app.exception
    study=next(w for w in app.selectbox if w.label=='Estudo a revisar')
    assert study.value=='s2'
    next(w for w in app.selectbox if w.label=='Mostrar na minha fila').set_value('Minha revisão registrada').run()
    assert not app.exception
    assert next(w for w in app.selectbox if w.label=='Estudo a revisar').value=='s1'
    assert not writes and history(workspace)==before


@pytest.mark.requirement('REQ-CLN-008')
def test_personal_ui_refreshes_to_next_pending_study_only_after_human_submit(workspace,monkeypatch):
    from streamlit.testing.v1 import AppTest
    writes=ui_client(workspace,R1,monkeypatch)
    app=AppTest.from_string(ui_script()).run()
    assert not app.exception and not writes
    assert next(w for w in app.selectbox if w.label=='Estudo a revisar').value=='s1'
    next(w for w in app.text_area if w.label=='Justificativa e material consultado').set_value('Synthetic human review: insufficient permitted evidence')
    next(w for w in app.button if w.label=='Salvar triagem humana').click().run()
    assert not app.exception and len(writes)==1
    assert writes[0]['study_id']=='s1' and writes[0]['decision']=='INCERTO'
    assert next(w for w in app.selectbox if w.label=='Estudo a revisar').value=='s2'
    assert next(w for w in app.text_area if w.label=='Justificativa e material consultado').value==''
    assert app.success and len(history(workspace))==1
