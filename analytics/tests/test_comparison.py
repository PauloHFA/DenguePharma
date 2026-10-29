import copy
from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
from urllib.error import HTTPError

import pyarrow as pa
import pytest
from fastapi.testclient import TestClient
from denguepharma_analytics.api import create_app
from denguepharma_analytics import comparison,storage,marts
from denguepharma_analytics.domain import digest,json_bytes
from denguepharma_analytics.sources.snapshot import load_snapshot


def published(root,data,*,publish=True):
    manifest=storage.export(load_snapshot(json_bytes(data)),root)
    if publish:storage.publish(root,manifest['run_id'])
    return manifest['run_id']


def updated(data):
    result=copy.deepcopy(data);result['documents'][0]['title']='=UNTRUSTED_FORMULA()'
    return result


@pytest.mark.requirement('REQ-MIG-014')
def test_comparison_known_counts_denominators_and_no_private_text(snapshot,tmp_path):
    before=published(tmp_path,snapshot.data);data=copy.deepcopy(snapshot.data)
    data['documents'].pop(1)
    data['documents'][0].update(contentHash=digest(b'new content'),versionId='new-version',version=2)
    added=copy.deepcopy(snapshot.data['documents'][1]);added.update(documentId='p3',versionId='v-p3',contentHash=digest(b'p3'))
    added['metadata'].update(pmid='999',doi='10.1000/new');data['documents'].append(added)
    current=published(tmp_path,data);result=comparison.compare(tmp_path,before,current)
    assert result['baseline_documents']==result['current_documents']==3 and result['shared_documents']==2
    assert {k:v for k,v in result['counts'].items() if v}==dict(NOVO=1,NAO_OBSERVADO=1,CONTEUDO_ALTERADO=1,INALTERADO=1)
    metrics={r['change_kind']:r for r in result['metrics']}
    assert metrics['NOVO']['denominator']==3 and metrics['NOVO']['proportion']==pytest.approx(1/3)
    assert metrics['CONTEUDO_ALTERADO']['denominator']==2 and metrics['CONTEUDO_ALTERADO']['proportion']==.5
    assert all(not r['table'].startswith('silver_') for r in result['table_changes'])
    assert 'PRIVATE_' not in json.dumps(result) and 'abstract' not in json.dumps(result)
    assert result==comparison.compare(tmp_path,before,current)


@pytest.mark.requirement('REQ-MIG-014')
def test_comparison_distinguishes_representations_references_and_retrieval(snapshot,tmp_path):
    before=published(tmp_path,snapshot.data);data=copy.deepcopy(snapshot.data)
    data['documents'][0]['metadata']['pub_year']='2026'
    data['documents'][1]['versionId']='different-reference'
    data['documents'][2]['retrievedAt']='2026-10-28T12:00:00Z'
    current=published(tmp_path,data);result=comparison.compare(tmp_path,before,current)
    assert result['counts']['REPRESENTACAO_ALTERADA']==result['counts']['REFERENCIA_ALTERADA']==result['counts']['DATA_RECUPERACAO_ALTERADA']==1
    assert result['counts']['CONTEUDO_ALTERADO']==0 and not result['same_input']
    assert all(r['previous_content_hash']==r['current_content_hash'] for r in result['document_changes'])


@pytest.mark.requirement('REQ-MIG-014')
def test_comparison_rejects_different_scope_without_interpreting_counts(snapshot,tmp_path):
    before=published(tmp_path,snapshot.data)
    from denguepharma_analytics.clinical.workspace import create
    protocol=json.loads((Path(__file__).resolve().parents[2]/'spec/clinical/protocolo.json').read_bytes())
    clinical=create(tmp_path/'private-curation',snapshot,protocol).freeze()
    changes=[lambda d:d['protocol'].update(id='foreign'),lambda d:d['protocol'].update(cutoff_date='2026-01-01'),
        lambda d:d['protocol'].update(maxRecordsPerSource=0),lambda d:d.update(filters={'source':'PUBMED'}),
        lambda d:d['sourceRuns'][0].update(query='another query'),lambda d:d.update(clinical=clinical)]
    for edit in changes:
        data=copy.deepcopy(snapshot.data);edit(data);current=published(tmp_path,data)
        with pytest.raises(ValueError,match='INCOMPATIBLE_COMPARISON'):comparison.compare(tmp_path,before,current)


@pytest.mark.requirement('REQ-MIG-014')
def test_comparison_empty_is_not_perfect_and_requires_published_integrity(snapshot,tmp_path):
    data=copy.deepcopy(snapshot.data);data['documents']=[]
    empty=published(tmp_path,data);result=comparison.compare(tmp_path,empty,empty)
    assert result['same_input'] and result['baseline_documents']==0 and not result['document_changes']
    assert all(r['proportion'] is None and r['denominator']==0 for r in result['metrics'])
    private=published(tmp_path,snapshot.data,publish=False)
    with pytest.raises(FileNotFoundError):comparison.compare(tmp_path,empty,private)
    with pytest.raises(ValueError,match='INVALID_RUN_ID'):comparison.compare(tmp_path,'../private',empty)
    app=TestClient(create_app(tmp_path))
    assert app.get('/api/public/comparisons',params=dict(baseline=empty,current=private)).status_code==404
    (tmp_path/'runs'/empty/'summary.json').write_text('{}')
    with pytest.raises(ValueError,match='ARTIFACT_HASH'):comparison.compare(tmp_path,empty,empty)


@pytest.mark.requirement('REQ-MIG-014')
def test_comparison_cli_api_artifacts_equivalence_and_immutable_export(snapshot,tmp_path):
    before=published(tmp_path,snapshot.data);current=published(tmp_path,updated(snapshot.data))
    result=comparison.compare(tmp_path,before,current);app=TestClient(create_app(tmp_path));params=dict(baseline=before,current=current)
    assert app.get('/api/public/comparisons',params=params).json()==result
    response=app.get('/api/public/comparisons/artifacts',params={**params,'name':'document_changes.csv'})
    assert response.status_code==200 and "'=UNTRUSTED_FORMULA()" in response.text and 'PRIVATE_' not in response.text
    assert app.get('/api/public/comparisons/artifacts',params={**params,'name':'../snapshot.json'}).status_code==404
    command=[sys.executable,'-m','denguepharma_analytics.cli','--data-dir',str(tmp_path),'compare','--baseline',before,'--current',current]
    cli=subprocess.run(command,capture_output=True,text=True,timeout=30)
    assert cli.returncode==0,cli.stderr
    assert json.loads(cli.stdout)==result
    output=tmp_path/'comparison';saved=comparison.export(result,output)
    assert not saved['reused'] and comparison.export(result,output)['reused']
    manifest=json.loads((output/'manifest.json').read_bytes())
    for name,hash_ in manifest['artifacts'].items():assert digest((output/name).read_bytes())==hash_
    (output/'document_changes.csv').write_text('changed')
    with pytest.raises(ValueError,match='IMMUTABLE_COMPARISON'):comparison.export(result,output)


@pytest.mark.requirement('REQ-MIG-014')
def test_comparison_same_input_separates_schema_changes_from_new_evidence(snapshot,tmp_path,monkeypatch):
    before=published(tmp_path,snapshot.data)
    monkeypatch.setattr(storage,'__version__','SYNTHETIC-NEXT')
    schema=marts.SCHEMAS['clinical_results'];monkeypatch.setitem(marts.SCHEMAS,'clinical_results',pa.schema(list(schema)+[pa.field('synthetic_new_column',pa.string())]))
    current=published(tmp_path,snapshot.data);result=comparison.compare(tmp_path,before,current)
    assert result['same_input'] and result['document_changes']==[] and result['counts']['INALTERADO']==3
    row=next(r for r in result['table_changes'] if r['table']=='clinical_results')
    assert row['status']=='SCHEMA_ALTERADO' and row['schema_changed'] and not row['data_changed']
    assert row['previous_rows']==row['current_rows']==0


def interface(monkeypatch,*,error=False,other=False):
    from streamlit.testing.v1 import AppTest
    from denguepharma_analytics import client
    calls=[]
    def get(path):
        calls.append(path)
        if error:raise HTTPError(path,409,'incompatible',None,BytesIO(b'{"detail":"INCOMPATIBLE_COMPARISON:protocol"}'))
        return dict(comparison_id='test-only',baseline_documents=3,current_documents=3,shared_documents=3,same_input=True,notice='Synthetic comparison only',
            metrics=[dict(change_kind='INALTERADO',count=3,denominator=3,proportion=1,unit='documento')],document_changes=[],table_changes=[])
    monkeypatch.setattr(client,'get',get)
    runs=[dict(id='current',protocol={'id':'p'},document_count=3),dict(id='baseline',protocol={'id':'other' if other else 'p'},document_count=3)]
    app=AppTest.from_string('from denguepharma_analytics.comparison_ui import render\nrender("current",'+repr(runs)+')',default_timeout=30).run()
    return app,calls


@pytest.mark.requirement('REQ-MIG-014')
def test_comparison_form_requires_baseline_and_exports_public_results(monkeypatch):
    app,calls=interface(monkeypatch)
    assert not app.exception and app.button[0].disabled and not calls
    app.selectbox[0].select('baseline').run();app.button[0].click().run()
    assert not app.exception and not app.error and len(calls)==1
    assert len(app.get('link_button'))==4 and any('Mesma entrada congelada' in info.value for info in app.info)


@pytest.mark.requirement('REQ-MIG-014')
def test_comparison_form_handles_incompatibility_and_missing_reference(monkeypatch):
    app,calls=interface(monkeypatch,error=True)
    app.selectbox[0].select('baseline').run();app.button[0].click().run()
    assert not app.exception and app.error and 'INCOMPATIBLE_COMPARISON' in app.error[0].value
    assert not app.get('link_button') and len(calls)==1
    other,calls=interface(monkeypatch,other=True)
    assert not other.exception and other.info and not other.button and not other.selectbox and not calls
