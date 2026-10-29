import copy
import csv
from io import BytesIO,StringIO
import json
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient
from test_clinical import workspace,R1,R2,include,result,approve
from denguepharma_analytics.api import create_app
from denguepharma_analytics.clinical.models import Principal
from denguepharma_analytics.clinical.extraction_coverage import view,package
from denguepharma_analytics.domain import digest


def history(workspace):
    with workspace.transaction() as db:return workspace.events(db)


@pytest.mark.requirement('REQ-CLN-009')
def test_coverage_has_no_synthetic_cells_before_independent_inclusion(workspace):
    before=history(workspace);data=view(workspace,R1)
    assert data['included_studies']==0 and data['cells']==[]
    assert data['cells_with_reviewed_results']==data['cells_without_reviewed_results']==0
    assert not data['calibration_approved']
    assert data['protocol_outcomes']==len(workspace.protocol['outcomes'])
    assert history(workspace)==before


@pytest.mark.requirement('REQ-CLN-009')
def test_coverage_counts_only_reviewed_results_without_document_duplicates(workspace):
    include(workspace);data=view(workspace,R1)
    assert data['included_studies']==1 and len(data['cells'])==len(workspace.protocol['outcomes'])
    assert all(c['status']=='SEM_RESULTADO_REVISADO' for c in data['cells'])
    payload=result(workspace)
    draft=workspace.act('RESULT_DRAFTED',payload,R1)
    assert view(workspace,R1)['cells_with_reviewed_results']==0
    approve(workspace,payload);approve(workspace,copy.deepcopy(payload))
    reviewed=view(workspace,R1)
    cell=next(c for c in reviewed['cells'] if c['outcome_code']=='EVENTOS_ADVERSOS')
    assert cell['reviewed_result_count']==cell['reviewed_comparison_count']==1
    assert len(cell['result_ids'])==1 and not cell['has_conflict']
    assert reviewed['cells_with_reviewed_results']==1
    assert reviewed['cells_without_reviewed_results']==len(workspace.protocol['outcomes'])-1
    assert cell['status']=='COM_RESULTADO_REVISADO' and not reviewed['calibration_approved']
    assert draft['event_id'] not in cell['result_ids']


@pytest.mark.requirement('REQ-CLN-009')
def test_coverage_preserves_conflicts_even_when_another_comparison_is_reviewed(workspace):
    include(workspace);payload=result(workspace)
    approve(workspace,payload)
    conflicting=copy.deepcopy(payload);conflicting['treatment']['events']=5
    approve(workspace,conflicting)
    cell=next(c for c in view(workspace,R1)['cells'] if c['outcome_code']=='EVENTOS_ADVERSOS')
    assert cell['status']=='CONFLITO_PENDENTE' and cell['reviewed_result_count']==0
    independent=copy.deepcopy(payload);independent['comparison_id']='separate-synthetic-comparison'
    approve(workspace,independent)
    data=view(workspace,R1);cell=next(c for c in data['cells'] if c['outcome_code']=='EVENTOS_ADVERSOS')
    assert data['cells_with_conflicts']==data['cells_with_reviewed_results']==1
    assert cell['has_conflict'] and cell['status']=='CONFLITO_PENDENTE' and cell['reviewed_result_count']==1


@pytest.mark.requirement('REQ-CLN-009')
def test_coverage_drops_stale_evidence_and_does_not_restore_it_after_rescreening(workspace):
    include(workspace);approve(workspace,result(workspace))
    assert view(workspace,R1)['cells_with_reviewed_results']==1
    workspace.attach_source(workspace.input.data['documents'][0],'Synthetic changed permitted source')
    assert view(workspace,R1)['cells']==[]
    include(workspace)
    current=view(workspace,R1)
    assert current['included_studies']==1 and current['cells_with_reviewed_results']==0


@pytest.mark.requirement('REQ-CLN-009')
def test_coverage_export_is_reproducible_private_and_requires_permissions(workspace,tmp_path):
    include(workspace);approve(workspace,result(workspace));before=history(workspace)
    first=package(workspace,R1);assert first==package(workspace,R2)
    with ZipFile(BytesIO(first)) as archive:
        manifest=json.loads(archive.read('manifest.json'))
        for name,hash_ in manifest['artifacts'].items():assert digest(archive.read(name))==hash_
        rows=list(csv.DictReader(StringIO(archive.read('coverage.csv').decode())))
        assert len(rows)==len(workspace.protocol['outcomes'])
        for forbidden in [b'PRIVATE_KEY',b'PRIVATE_CONTACT',R1.id.encode(),R2.id.encode(),b'quote',b'events']:
            assert forbidden not in archive.read('coverage.csv')+archive.read('summary.json')
    app=TestClient(create_app(tmp_path,authenticate=lambda token:R1 if token=='reviewer' else Principal('reader',('LEITOR',))))
    url=f'/api/clinical/{workspace.key}/extraction-coverage'
    assert app.get(url).status_code==401
    assert app.get(url+'/export',headers={'Authorization':'Bearer reader'}).status_code==403
    headers={'Authorization':'Bearer reviewer'}
    response=app.get(url,headers=headers)
    assert response.status_code==200 and response.headers['Cache-Control']=='no-store'
    downloaded=app.get(url+'/export',headers=headers)
    assert downloaded.content==first and downloaded.headers['Cache-Control']=='no-store'
    assert history(workspace)==before


@pytest.mark.requirement('REQ-CLN-009')
def test_coverage_ui_explains_empty_state_and_export_does_not_create_decisions(workspace,monkeypatch):
    from streamlit.testing.v1 import AppTest
    from denguepharma_analytics import client
    def private(path,**kwargs):
        return package(workspace,R1) if path.endswith('/export') else view(workspace,R1)
    monkeypatch.setattr(client,'private',private)
    app=AppTest.from_string("from denguepharma_analytics.clinical.extraction_coverage_ui import render\nrender('workspace','synthetic-token')").run()
    assert not app.exception and app.info
    assert not app.selectbox and not app.dataframe
    app.button[0].click().run()
    assert not app.exception and history(workspace)==[]
