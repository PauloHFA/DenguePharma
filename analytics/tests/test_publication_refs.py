import copy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient
from denguepharma_analytics.api import create_app
from denguepharma_analytics.analyses.publication_refs import analyze,pmid,figures
from denguepharma_analytics.domain import digest,json_bytes
from denguepharma_analytics.sources.snapshot import load_snapshot
from denguepharma_analytics.storage import export,publish


def source(snapshot,references):
    data=copy.deepcopy(snapshot.data)
    data['documents'][-1]['metadata']['protocolSection']['referencesModule']={'references':references}
    return data


@pytest.mark.requirement('REQ-MIG-017')
def test_publication_refs_known_coverage_deduplication_and_privacy(snapshot):
    data=source(snapshot,[{'type':'RESULT','pmid':'123'},{'type':'RESULT','pmid':'00123'},{'type':'RESULT','pmid':'456'},
        {'type':'DERIVED','pmid':'123'},{'type':'BACKGROUND','pmid':'789','citation':'PRIVATE_CITATION'},
        {'type':'BACKGROUND','pmid':'PRIVATE_BAD_IDENTIFIER'},{'type':'BACKGROUND'}])
    summary,tables=analyze(data);result=next(r for r in summary['coverage'] if r['reference_type']=='RESULT')
    assert summary['registry_units']==1 and summary['publication_documents']==2 and summary['publications_with_distinct_pmid']==1
    assert result['distinct_valid_pmids']==2 and result['valid_pmids_in_corpus']==1 and result['pmid_coverage_proportion']==.5
    assert result['registry_units_with_candidate']==1 and result['registry_reference_proportion']==1
    row=next(r for r in tables['publication_reference_links'] if r['pmid']=='123' and r['reference_type']=='RESULT')
    assert len(row['observations'])==2 and row['publication_document_ids']==['p1','p2']
    assert row['status']=='CANDIDATO_NO_CORPUS' and row['automatically_confirmed'] is False
    assert summary['missing_distinct_pmids']==2 and 'PRIVATE_' not in json.dumps(tables)


@pytest.mark.requirement('REQ-MIG-017')
def test_publication_refs_do_not_infer_result_links_from_indicators_or_legacy_identity(snapshot,tmp_path):
    data=source(snapshot,[]);trial=data['documents'][-1];trial['metadata']['hasResults']=True;trial['studyLinks'][0]['study_id']='s1'
    summary,tables=analyze(data);result=next(r for r in summary['coverage'] if r['reference_type']=='RESULT')
    assert result['registry_units_with_references']==0 and result['pmid_coverage_proportion'] is None
    assert not tables['publication_reference_links']
    trial['metadata']['protocolSection']['referencesModule']['references']=[{'type':'DERIVED','pmid':'123'}]
    summary,tables=analyze(data)
    assert next(r for r in summary['coverage'] if r['reference_type']=='RESULT')['distinct_valid_pmids']==0
    assert tables['publication_reference_links'][0]['reference_type']=='DERIVED' and not tables['publication_reference_links'][0]['automatically_confirmed']
    empty=copy.deepcopy(data);empty['documents']=[];summary,tables=analyze(empty)
    assert all(r['pmid_coverage_proportion'] is None and r['registry_reference_proportion'] is None for r in summary['coverage'])
    figures(summary,tmp_path/'empty');assert not (tmp_path/'empty').exists()


@pytest.mark.requirement('REQ-MIG-017')
def test_publication_refs_repeated_trials_and_overlapping_types_preserve_provenance(snapshot):
    data=source(snapshot,[{'type':'RESULT','pmid':'456'}]);second=copy.deepcopy(data['documents'][-1])
    second.update(documentId='second',versionId='v-second',contentHash=digest(b'second'));data['documents'].append(second)
    summary,tables=analyze(data)
    assert summary['registry_units']==1 and len(tables['publication_reference_links'])==1
    assert len(tables['publication_reference_links'][0]['trial_references'])==2
    second['metadata']['protocolSection']['identificationModule']['nctId']='NCT00000002'
    second['metadata']['protocolSection']['referencesModule']['references']=[{'type':'BACKGROUND','pmid':'456'}]
    summary,tables=analyze(data);gap=tables['publication_reference_missing'][0]
    assert summary['registry_units']==2 and summary['missing_distinct_pmids']==1
    assert gap['trial_ids']==['NCT00000001','NCT00000002'] and gap['reference_types']==['BACKGROUND','RESULT']


@pytest.mark.requirement('REQ-MIG-017')
def test_publication_refs_missing_invalid_identifiers_and_unknown_types(snapshot):
    assert pmid(' 000123 ')==('123','PRESENTE') and pmid('0')==(None,'INVALIDO')
    assert pmid(123)==pmid(False)==(None,'INVALIDO') and pmid(None)==(None,'NAO_INFORMADO')
    data=source(snapshot,[{'pmid':'123'},{'type':'OTHER_TYPE','pmid':'0'},{'type':'RESULT'}])
    summary,tables=analyze(data)
    assert {'NAO_INFORMADO','OTHER_TYPE'}.issubset(r['reference_type'] for r in summary['coverage'])
    assert all(r['source_url'] is None for r in tables['publication_reference_links'] if r['pmid'] is None)
    invalid=source(snapshot,[None])
    with pytest.raises(ValueError,match='PUBLICATION_REFERENCE_METADATA_INVALID'):analyze(invalid)
    invalid=copy.deepcopy(data);other=copy.deepcopy(invalid['documents'][0]);other['metadata']['pmid']='999';invalid['documents'].append(other)
    with pytest.raises(ValueError,match='CONFLICTING_PUBLICATION_IDENTIFIER'):analyze(invalid)


@pytest.mark.requirement('REQ-MIG-017')
def test_publication_refs_cli_api_png_parquet_and_quarto_are_equivalent(snapshot,tmp_path):
    raw=json_bytes(source(snapshot,[{'type':'RESULT','pmid':'123'},{'type':'RESULT','pmid':'456'}]));path=tmp_path/'input.json';path.write_bytes(raw);root=tmp_path/'data'
    manifest=export(load_snapshot(raw),root);publish(root,manifest['run_id']);run=manifest['run_id']
    command=[sys.executable,'-m','denguepharma_analytics.cli','--data-dir',str(root),'prepare','--input',str(path),'--expected-hash',digest(raw)]
    done=subprocess.run(command,capture_output=True,text=True,timeout=40);assert done.returncode==0,done.stderr
    assert json.loads(done.stdout)['run_id']==run and len(manifest['tables'])==39
    app=TestClient(create_app(root));prefix='/api/public/analyses/'+run
    assert app.get(prefix+'/summary').json()['publication_references']['missing_distinct_pmids']==1
    rows=app.get(prefix+'/tables/publication_reference_links').json()['rows'];assert len(rows)==2 and all(not r['automatically_confirmed'] for r in rows)
    png=app.get(prefix+'/artifacts',params={'name':'figures/publication-refs-coverage.png'})
    assert png.status_code==200 and digest(png.content)==manifest['artifacts']['figures/publication-refs-coverage.png']
    assert 'PRIVATE_' not in json.dumps(rows)
    if os.getenv('QUARTO_BIN'):
        from denguepharma_analytics.reports.render import render
        render(root,run,os.environ['QUARTO_BIN']);html=app.get(prefix+'/artifacts',params={'name':'report.html'}).text
        assert 'cobertura por PMID' in html and 'NAO_RECUPERADO_NO_CORPUS' in html


@pytest.mark.requirement('REQ-MIG-017')
def test_publication_refs_derived_metadata_preserves_previous_thirty_six_tables(snapshot):
    from denguepharma_analytics.analyses.diagnostics import analyze as diagnostics
    from denguepharma_analytics.marts import build_tables
    old=snapshot.data;new=source(snapshot,[{'type':'DERIVED','pmid':'123'}])
    before=build_tables(old,*diagnostics(json_bytes(old)));after=build_tables(new,*diagnostics(json_bytes(new)))
    names=[n for n in before if not n.startswith('publication_reference_')]
    assert len(names)==36 and all(before[n].equals(after[n]) for n in names)
    assert not before['publication_reference_links'].equals(after['publication_reference_links'])


@pytest.mark.requirement('REQ-MIG-017')
def test_publication_refs_form_preserves_warning_and_supports_old_empty_runs(snapshot,monkeypatch):
    from streamlit.testing.v1 import AppTest
    from denguepharma_analytics import client
    from denguepharma_analytics.marts import normalize_rows,SCHEMAS
    summary,tables=analyze(source(snapshot,[{'type':'DERIVED','pmid':'123'}]));calls=[]
    monkeypatch.setattr(client,'table',lambda run,name,**kwargs:calls.append(name) or dict(rows=normalize_rows(tables[name],SCHEMAS[name]),total=len(tables[name])))
    script='from denguepharma_analytics.publication_refs_ui import render\nrender("run",'+repr({'tables':dict.fromkeys(tables),'figures':{}})+','+repr({'publication_references':summary})+')'
    app=AppTest.from_string(script,default_timeout=30).run()
    assert not app.exception and app.warning and len(app.get('link_button'))==3 and len(calls)==2
    old=AppTest.from_string('from denguepharma_analytics.publication_refs_ui import render\nrender("old",{"tables":{}},{})',default_timeout=30).run()
    assert not old.exception and old.info and not old.get('link_button')
    empty,_=analyze({'documents':[]})
    app=AppTest.from_string('from denguepharma_analytics.publication_refs_ui import render\nrender("empty",'+repr({'tables':dict.fromkeys(tables)})+','+repr({'publication_references':empty})+')',default_timeout=30).run()
    assert not app.exception and app.info and not app.get('link_button')


@pytest.mark.requirement('REQ-MIG-017')
def test_publication_refs_real_frozen_pilots_match_metadata_audit():
    if os.getenv('ANALYTICS_LIVE_POSTGRES')!='true':pytest.skip('Local frozen pilot verification disabled')
    root=Path(__file__).resolve().parents[2]/'analytics/data/snapshots/sponsors-0.12'
    clinical,tables=analyze(json.loads((root/'clinical-20.json').read_bytes()));result=next(r for r in clinical['coverage'] if r['reference_type']=='RESULT')
    assert result['registry_units_with_references']==0 and result['distinct_valid_pmids']==0 and result['pmid_coverage_proportion'] is None
    assert clinical['missing_distinct_pmids']==71 and all(not r['automatically_confirmed'] for r in tables['publication_reference_links'])
    operational,_=analyze(json.loads((root/'operational-50.json').read_bytes()));result=next(r for r in operational['coverage'] if r['reference_type']=='RESULT')
    assert result['registry_units_with_references']==2 and result['distinct_valid_pmids']==28 and result['valid_pmids_in_corpus']==0
    assert operational['missing_distinct_pmids']==69
