import copy
import json

import pytest
from fastapi.testclient import TestClient
from test_clinical import workspace, R1, R2, ADJ, screen
from denguepharma_analytics.api import create_app
from denguepharma_analytics.clinical.models import Principal
from denguepharma_analytics.clinical.selection_flow import view, export_summary, CATEGORIES
from denguepharma_analytics.clinical.workspace import create
from denguepharma_analytics.domain import json_bytes
from denguepharma_analytics.sources.snapshot import load_snapshot


def exclude(workspace, study='s1'):
    screen(workspace, R1, study=study, decision='EXCLUIR')
    screen(workspace, R2, study=study, decision='EXCLUIR')


def annotation(workspace, study='s1', **changes):
    row = next(r for r in view(workspace, ADJ)['excluded_studies'] if r['study_id'] == study)
    return dict(study_id=study, resolution_hash=row['resolution_hash'],
        category='DESENHO_NAO_ELEGIVEL', reason='Synthetic protocol criterion checked manually', **changes)


def events(workspace):
    with workspace.transaction() as db: return workspace.events(db)


@pytest.mark.requirement('REQ-CLN-001')
def test_selection_flow_preserves_units_pending_values_and_blinding(workspace):
    initial = view(workspace, R1)
    assert initial['document_count'] == 3 and initial['study_identity_count'] == 2
    assert initial['statuses'] == dict(PENDENTE=2, INCERTO=0, CONFLITO=0, INCLUIR=0, EXCLUIR=0)
    assert not initial['selection_complete']
    assert all(initial['identification'][key] is None for key in
        ('identified_records', 'removed_duplicates', 'screened_records'))
    assert all(r['count'] == 0 for r in initial['exclusion_reasons'])
    screen(workspace, R2, decision='EXCLUIR')
    pending = view(workspace, R1)
    assert pending['statuses']['PENDENTE'] == 2 and pending['exclusions_without_current_reason'] == 0
    assert pending['excluded_studies'] == []
    assert R2.id not in json.dumps(pending) and 'classification' not in json.dumps(pending)
    assert len(events(workspace)) == 1


@pytest.mark.requirement('REQ-CLN-001')
def test_selection_flow_annotation_is_human_and_never_changes_screening(workspace):
    exclude(workspace)
    before = view(workspace, ADJ)
    assert before['exclusions_without_current_reason'] == 1
    assert all(r['count'] == 0 for r in before['exclusion_reasons'])
    assert before['excluded_studies'][0]['annotation'] is None
    decision = annotation(workspace)
    workspace.act('EXCLUSION_REASON_RECORDED', decision, ADJ)
    after = view(workspace, ADJ)
    assert after['statuses'] == before['statuses']
    assert after['selection_hash'] == before['selection_hash']
    assert after['exclusions_without_current_reason'] == 0
    assert sum(r['count'] for r in after['exclusion_reasons']) == 1
    assert after['excluded_studies'][0]['annotation']['category'] == 'DESENHO_NAO_ELEGIVEL'
    assert len(events(workspace)) == 3 and events(workspace)[-1]['kind'] == 'EXCLUSION_REASON_RECORDED'
    assert not workspace.freeze()['results']
    changed = {**decision, 'category':'OUTRO_CRITERIO_PROTOCOLO', 'reason':'Synthetic corrected primary protocol reason'}
    workspace.act('EXCLUSION_REASON_RECORDED', changed, ADJ)
    rows = {r['category']: r['count'] for r in view(workspace, R1)['exclusion_reasons']}
    assert rows['OUTRO_CRITERIO_PROTOCOLO'] == 1 and rows['DESENHO_NAO_ELEGIVEL'] == 0
    assert len(events(workspace)) == 4


@pytest.mark.requirement('REQ-CLN-001')
def test_selection_flow_rejects_ineligible_annotation_actions(workspace):
    exclude(workspace)
    data = annotation(workspace)
    with pytest.raises(PermissionError): workspace.act('EXCLUSION_REASON_RECORDED', data, R1)
    for category in ['SEM_TEXTO_INTEGRAL', 'DUPLICADO', 'category-invented']:
        with pytest.raises(ValueError):
            workspace.act('EXCLUSION_REASON_RECORDED', {**data, 'category':category}, ADJ)
    with pytest.raises(ValueError, match='RESOLVED_EXCLUSION_REQUIRED'):
        workspace.act('EXCLUSION_REASON_RECORDED', {**data, 'study_id':'s2'}, ADJ)
    with pytest.raises(ValueError, match='STALE_EXCLUSION_RESOLUTION'):
        workspace.act('EXCLUSION_REASON_RECORDED', {**data, 'resolution_hash':'0'*64}, ADJ)
    assert len(events(workspace)) == 2


@pytest.mark.requirement('REQ-CLN-001')
def test_selection_flow_vote_and_source_changes_do_not_reactivate_annotations(workspace):
    exclude(workspace)
    old = annotation(workspace)
    workspace.act('EXCLUSION_REASON_RECORDED', old, ADJ)
    screen(workspace, R1, decision='INCLUIR')
    assert view(workspace, ADJ)['statuses']['CONFLITO'] == 1
    assert sum(r['count'] for r in view(workspace, ADJ)['exclusion_reasons']) == 0
    screen(workspace, R1, decision='EXCLUIR')
    current = view(workspace, ADJ)
    assert current['exclusions_without_current_reason'] == 1
    assert current['excluded_studies'][0]['annotation'] is None
    with pytest.raises(ValueError, match='STALE_EXCLUSION_RESOLUTION'):
        workspace.act('EXCLUSION_REASON_RECORDED', old, ADJ)
    workspace.act('EXCLUSION_REASON_RECORDED', annotation(workspace), ADJ)
    workspace.attach_source(workspace.input.data['documents'][0], 'Synthetic permitted new source')
    assert view(workspace, ADJ)['statuses']['PENDENTE'] == 2
    assert sum(r['count'] for r in view(workspace, ADJ)['exclusion_reasons']) == 0


@pytest.mark.requirement('REQ-CLN-001')
def test_selection_flow_adjudication_changes_invalidate_reason(workspace):
    screen(workspace, R1, decision='INCLUIR')
    screen(workspace, R2, decision='EXCLUIR')
    row = next(r for r in workspace.queue(ADJ) if r['study_id']=='s1')
    payload = dict(study_id='s1', basis_hash=row['basis_hash'], votes_hash=row['adjudication']['votes_hash'],
        decision='EXCLUIR', classification=row['adjudication']['votes'][0]['classification'], reason='Synthetic independently adjudicated exclusion')
    workspace.act('SCREEN_ADJUDICATED', payload, ADJ)
    old = annotation(workspace)
    workspace.act('EXCLUSION_REASON_RECORDED', old, ADJ)
    # A new adjudication requires a current conflict, not a silent overwrite.
    with pytest.raises(ValueError, match='SCREENING_CONFLICT_REQUIRED'):
        workspace.act('SCREEN_ADJUDICATED', payload, ADJ)
    screen(workspace, R1, decision='EXCLUIR')
    screen(workspace, R1, decision='INCLUIR')
    current = next(r for r in workspace.queue(ADJ) if r['study_id']=='s1')
    workspace.act('SCREEN_ADJUDICATED', {**payload,
        'votes_hash':current['adjudication']['votes_hash'],
        'reason':'Synthetic new adjudication of changed independent votes'}, ADJ)
    assert view(workspace, ADJ)['exclusions_without_current_reason'] == 1
    with pytest.raises(ValueError, match='STALE_EXCLUSION_RESOLUTION'):
        workspace.act('EXCLUSION_REASON_RECORDED', old, ADJ)


@pytest.mark.requirement('REQ-CLN-001')
def test_selection_flow_identity_and_empty_corpus_do_not_invent_totals(workspace, tmp_path):
    exclude(workspace)
    workspace.act('EXCLUSION_REASON_RECORDED', annotation(workspace), ADJ)
    workspace.act('DOCUMENT_LINKED', dict(document_id='p1',study_id='s2',reason='Synthetic source link manually checked'), ADJ)
    after = view(workspace, ADJ)
    assert after['document_count'] == 3 and after['study_identity_count'] == 2
    assert after['statuses']['PENDENTE'] == 2 and sum(r['count'] for r in after['exclusion_reasons']) == 0
    data = copy.deepcopy(workspace.input.data); data['documents'] = []
    empty = create(tmp_path/'empty', load_snapshot(json_bytes(data)), workspace.protocol)
    summary = view(empty, R1)
    assert summary['document_count'] == summary['study_identity_count'] == 0
    assert not summary['selection_complete'] and summary['identification']['removed_duplicates'] is None
    assert sum(summary['statuses'].values()) == 0


@pytest.mark.requirement('REQ-CLN-001')
def test_selection_flow_export_permissions_totals_and_no_private_rationales(workspace, tmp_path):
    exclude(workspace)
    workspace.act('EXCLUSION_REASON_RECORDED', annotation(workspace), ADJ)
    screen(workspace, R1, study='s2'); screen(workspace, R2, study='s2')
    first = export_summary(workspace, ADJ)
    assert first == export_summary(workspace, R1) and first['selection_complete']
    assert sum(first['statuses'].values()) == 2
    assert sum(r['count'] for r in first['exclusion_reasons']) + first['exclusions_without_current_reason'] == first['statuses']['EXCLUIR']
    for forbidden in ['Synthetic protocol', R1.id, R2.id, ADJ.id, 'excluded_studies', 'PRIVATE_KEY']:
        assert forbidden not in json.dumps(first)
    app = TestClient(create_app(tmp_path, authenticate=lambda token: ADJ if token=='admin' else Principal('reader',('LEITOR',))))
    url = f'/api/clinical/{workspace.key}/selection-flow'
    assert app.get(url).status_code == 401
    assert app.get(url+'/export',headers={'Authorization':'Bearer reader'}).status_code == 403
    headers = {'Authorization':'Bearer admin'}
    response = app.get(url+'/export',headers=headers)
    assert response.status_code == 200 and response.json() == first
    assert response.headers['Cache-Control']=='no-store' and 'attachment;' in response.headers['Content-Disposition']
    before = events(workspace)
    assert app.post(f'/api/clinical/{workspace.key}/actions/EXCLUSION_REASON_RECORDED',headers={'Authorization':'Bearer reader'},json=annotation(workspace)).status_code == 403
    assert events(workspace) == before
    assert 'SEM_TEXTO_INTEGRAL' not in CATEGORIES and 'DUPLICADO' not in CATEGORIES


@pytest.mark.requirement('REQ-CLN-001')
def test_selection_flow_form_requires_explicit_category_and_confirmation(workspace, monkeypatch):
    from streamlit.testing.v1 import AppTest
    from denguepharma_analytics import client
    exclude(workspace)
    state = view(workspace, ADJ)
    writes = []
    def private(path, **kwargs):
        if path.endswith('/selection-flow'): return state
        writes.append((path, kwargs))
        return {'event_id':'synthetic-annotation'}
    monkeypatch.setattr(client, 'private', private)
    app = AppTest.from_string("from denguepharma_analytics.clinical.selection_flow_ui import render\nrender('workspace','private-token')").run()
    assert not app.exception and not writes
    app.selectbox[0].set_value('s1').run()
    assert not app.exception
    category = next(w for w in app.selectbox if w.label=='Motivo principal de exclusão')
    assert category.value is None
    submit = lambda: next(w for w in app.button if w.label=='Registrar motivo de exclusão')
    submit().click().run()
    assert not writes and app.error
    next(w for w in app.selectbox if w.label=='Motivo principal de exclusão').set_value('DESENHO_NAO_ELEGIVEL')
    app.text_area[0].set_value('Synthetic human checked protocol criterion')
    app.checkbox[0].check()
    submit().click().run()
    assert not app.exception and len(writes)==1
    assert writes[0][1]['data']['resolution_hash']==state['excluded_studies'][0]['resolution_hash']
    assert writes[0][1]['data']['category']=='DESENHO_NAO_ELEGIVEL'
    assert 'private-token' not in json.dumps(writes[0][1]['data'])


@pytest.mark.requirement("REQ-SEL-004")
def test_prisma_scr_flow_accounting_and_exclusion_categories():
    """REQ-SEL-004: identificados = duplicados + triados e exclusões somam por motivo."""
    from denguepharma_analytics.clinical.selection_flow import compute_prisma_flow
    reasons = {
        "POPULACAO_FORA_ESCOPO": 45,
        "CONTEXTO_FORA_ESCOPO": 30,
        "INTERVENCAO_NAO_ELEGIVEL": 15,
        "DESENHO_NAO_ELEGIVEL": 8,
        "OUTRO_CRITERIO_PROTOCOLO": 2,
    }
    # total_excluidos = 45 + 30 + 15 + 8 + 2 = 100
    # incluidos = 20
    # triados = 120
    # duplicados = 30
    # identificados = 150
    flow = compute_prisma_flow(
        identified_records=150,
        duplicates_removed=30,
        screened_records=120,
        included_records=20,
        exclusion_reasons=reasons,
    )
    assert flow["identified_records"] == 150
    assert flow["identified_records"] == flow["duplicates_removed"] + flow["screened_records"]
    assert flow["screened_records"] == flow["included_records"] + flow["excluded_records"]
    assert flow["excluded_records"] == sum(reasons.values()) == 100
    assert flow["formula_verified"] is True

    # Teste de violação contábil (identificados != duplicados + triados)
    with pytest.raises(ValueError, match="Inconsistência contábil"):
        compute_prisma_flow(
            identified_records=200,
            duplicates_removed=30,
            screened_records=120,
            included_records=20,
            exclusion_reasons=reasons,
        )

    # Teste de violação na soma das exclusões
    with pytest.raises(ValueError, match="Inconsistência contábil"):
        compute_prisma_flow(
            identified_records=150,
            duplicates_removed=30,
            screened_records=120,
            included_records=50,  # 50 + 100 != 120
            exclusion_reasons=reasons,
        )

