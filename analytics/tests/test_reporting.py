import copy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient
from denguepharma_analytics.api import create_app
from denguepharma_analytics.analyses.reporting import analyze,parse_date,figures,RESULT_STATES
from denguepharma_analytics.domain import json_bytes,digest
from denguepharma_analytics.sources.snapshot import load_snapshot
from denguepharma_analytics.storage import export,publish


def trial(snapshot,key,*,primary='2020-01-01',results='2020-01-11',has=True):
    doc=copy.deepcopy(snapshot.data['documents'][-1]);doc.update(documentId=key,versionId='v-'+key,contentHash=digest(key.encode()))
    section=doc['metadata']['protocolSection'];section['identificationModule']['nctId']='NCT'+str(int(key[1:])).zfill(8)
    module=section['statusModule'];module.update(overallStatus='COMPLETED',primaryCompletionDateStruct=dict(date=primary,type='ACTUAL'),lastUpdatePostDateStruct=dict(date='2020-02-01',type='ACTUAL'))
    if results is None:module.pop('resultsFirstPostDateStruct',None)
    else:module['resultsFirstPostDateStruct']=dict(date=results,type='ACTUAL')
    doc['metadata']['hasResults']=has
    return doc


def data(snapshot,documents):
    result=copy.deepcopy(snapshot.data);result['documents']=documents;return result


@pytest.mark.requirement('REQ-MIG-016')
def test_reporting_known_calendar_intervals_zero_and_fixed_cross_categories(snapshot):
    source=data(snapshot,[trial(snapshot,'t1',results='2020-01-01'),trial(snapshot,'t2'),trial(snapshot,'t3',results='2020-01-21'),trial(snapshot,'t4',results=None,has=False),trial(snapshot,'t5',results=None,has=None)])
    summary,tables=analyze(source);stats=summary['interval_summary']
    assert stats==dict(origin='primaryCompletionDateStruct.date',endpoint='resultsFirstPostDateStruct.date',observed=3,completed=5,total_trials=5,unit='dias_de_calendario',censoring=False,min=0,max=20,median=10.,q1=5.,q3=15.)
    rows=tables['reporting_registry'];assert next(r for r in rows if r['trial_id']=='NCT00000001')['interval_days']==0
    assert next(r for r in rows if r['trial_id']=='NCT00000004')['interval_days'] is None
    assert 'INDICADOR_NAO_INFORMADO' in next(r for r in rows if r['trial_id']=='NCT00000005')['flags']
    crossed=tables['reporting_results_by_status'];assert len(crossed)==4
    assert {r['result_category'] for r in crossed}==set(RESULT_STATES)
    assert sum(r['count'] for r in crossed)==5 and all(r['denominator']==5 for r in crossed)
    assert next(r for r in crossed if r['result_category']=='CONFLITO')['count']==0
    assert 'PRIVATE_' not in json.dumps(tables)


@pytest.mark.requirement('REQ-MIG-016')
def test_reporting_partial_estimated_invalid_future_negative_and_inconsistent_dates(snapshot):
    records=[trial(snapshot,'t1',primary='2020-01'),trial(snapshot,'t2'),trial(snapshot,'t3',primary='2020-02-30'),trial(snapshot,'t4',results='2019-12-31'),trial(snapshot,'t5',results='2027-01-01'),trial(snapshot,'t6'),trial(snapshot,'t7',has=False)]
    records[1]['metadata']['protocolSection']['statusModule']['resultsFirstPostDateStruct']['type']='ESTIMATED'
    records[5]['metadata']['protocolSection']['statusModule']['lastUpdatePostDateStruct']['date']='2027-01-01'
    unknown=trial(snapshot,'t8');unknown['metadata']['protocolSection']['statusModule']['overallStatus']='UNKNOWN';records.append(unknown)
    summary,tables=analyze(data(snapshot,records));rows=tables['reporting_registry']
    assert summary['interval_summary']['observed']==0 and all(r['interval_days'] is None for r in rows)
    expected=['PRIMARY_SEM_DATA_DIARIA','RESULTS_TIPO_NAO_ACTUAL','PRIMARY_SEM_DATA_DIARIA','RELATO_ANTES_CONCLUSAO_PRIMARIA','RESULTS_APOS_CORTE','LAST_UPDATE_APOS_CORTE','INDICADOR_E_DATA_DIVERGENTES','STATUS_NAO_DECLARADO_COMPLETED']
    for row,flag in zip(rows,expected):assert flag in row['flags']
    no_cutoff=data(snapshot,[trial(snapshot,'t8')]);no_cutoff['protocol']['cutoff_date']=None
    _,tables=analyze(no_cutoff);assert 'CORTE_INVALIDO_OU_AUSENTE' in tables['reporting_registry'][0]['flags']


@pytest.mark.requirement('REQ-MIG-016')
def test_reporting_duplicate_nct_conflicts_and_missing_observations_are_preserved(snapshot):
    first=trial(snapshot,'t1');second=copy.deepcopy(first);second.update(documentId='another',versionId='another-v',version=99,contentHash=digest(b'another'))
    second['metadata']['protocolSection']['statusModule']['resultsFirstPostDateStruct']['date']='2020-01-12'
    summary,tables=analyze(data(snapshot,[first,second]));row=tables['reporting_registry'][0]
    assert summary['trials']==1 and row['results_state']=='CONFLITO' and row['results_precision']=='CONFLITO'
    assert row['interval_days'] is None and len(row['references'])==len(row['observations'])==2
    second['metadata']['hasResults']=False
    _,tables=analyze(data(snapshot,[first,second]));row=tables['reporting_registry'][0]
    assert row['has_results'] is None and row['result_category']=='CONFLITO'
    second['metadata']['protocolSection']['statusModule']['overallStatus']='TERMINATED'
    _,tables=analyze(data(snapshot,[first,second]))
    assert any(r['overall_status']=='[CONFLITO]' for r in tables['reporting_results_by_status'])


@pytest.mark.requirement('REQ-MIG-016')
def test_reporting_date_precision_empty_data_and_native_boolean_contract(snapshot,tmp_path):
    assert parse_date('2020-02-29')['precision']=='DIA'
    assert parse_date('2019-02-29')['precision']=='INVALIDA'
    for text,precision in [('2020','ANO'),('2020-02','MES')]:
        value=parse_date(text);assert value['raw']==text and value['precision']==precision and value['value'] is None
    summary,tables=analyze(data(snapshot,[]));stats=summary['interval_summary']
    assert stats['observed']==0 and stats['median'] is None and stats['min'] is None
    assert not tables['reporting_registry'] and not tables['reporting_results_by_status']
    figures(summary,tmp_path/'empty');assert not (tmp_path/'empty').exists()
    invalid=trial(snapshot,'t1');invalid['metadata']['hasResults']='false'
    with pytest.raises(ValueError,match='REPORTING_METADATA_INVALID'):analyze(data(snapshot,[invalid]))


@pytest.mark.requirement('REQ-MIG-016')
def test_reporting_cli_api_parquet_png_and_quarto_are_equivalent(snapshot,tmp_path):
    raw=json_bytes(data(snapshot,[trial(snapshot,'t1')]))
    source=tmp_path/'source.json';source.write_bytes(raw);root=tmp_path/'data'
    manifest=export(load_snapshot(raw),root);publish(root,manifest['run_id']);run=manifest['run_id']
    command=[sys.executable,'-m','denguepharma_analytics.cli','--data-dir',str(root),'prepare','--input',str(source),'--expected-hash',digest(raw)]
    done=subprocess.run(command,capture_output=True,text=True,timeout=40)
    assert done.returncode==0,done.stderr
    assert json.loads(done.stdout)['run_id']==run and len(manifest['tables'])==39
    app=TestClient(create_app(root));prefix='/api/public/analyses/'+run
    summary=app.get(prefix+'/summary').json()['reporting'];assert summary['interval_summary']['median']==10
    rows=app.get(prefix+'/tables/reporting_registry').json()['rows'];assert rows[0]['interval_days']==10 and 'PRIVATE_' not in json.dumps(rows)
    png=app.get(prefix+'/artifacts',params={'name':'figures/reporting-intervals.png'})
    assert png.status_code==200 and digest(png.content)==manifest['artifacts']['figures/reporting-intervals.png']
    if os.getenv('QUARTO_BIN'):
        from denguepharma_analytics.reports.render import render
        render(root,run,os.environ['QUARTO_BIN']);html=app.get(prefix+'/artifacts',params={'name':'report.html'}).text
        assert 'auditoria de datas declaradas' in html.lower() and 'primaryCompletionDateStruct.date' in html


@pytest.mark.requirement('REQ-MIG-016')
def test_reporting_metadata_addition_preserves_previous_thirty_two_tables(snapshot):
    from denguepharma_analytics.analyses.diagnostics import analyze as diagnostics
    from denguepharma_analytics.marts import build_tables
    old=snapshot.data;new=copy.deepcopy(old)
    new['documents'][-1]['metadata']['protocolSection']['statusModule']['resultsFirstPostDateStruct']={'date':'2020-02-01','type':'ACTUAL'}
    before=build_tables(old,*diagnostics(json_bytes(old)));after=build_tables(new,*diagnostics(json_bytes(new)))
    names=[n for n in before if not n.startswith(('reporting_','publication_reference_'))]
    assert len(names)==32 and all(before[n].equals(after[n]) for n in names)
    assert not before['reporting_registry'].equals(after['reporting_registry'])


@pytest.mark.requirement('REQ-MIG-016')
def test_reporting_form_supports_current_old_and_empty_runs(snapshot,monkeypatch):
    from streamlit.testing.v1 import AppTest
    from denguepharma_analytics import client
    from denguepharma_analytics.marts import normalize_rows,SCHEMAS
    summary,tables=analyze(data(snapshot,[trial(snapshot,'t1')]));calls=[]
    monkeypatch.setattr(client,'table',lambda run,name,**kwargs:calls.append(name) or dict(rows=normalize_rows(tables[name],SCHEMAS[name]),total=len(tables[name])))
    script='from denguepharma_analytics.reporting_ui import render\nrender("run",'+repr({'tables':dict.fromkeys(tables),'figures':{}})+','+repr({'reporting':summary})+')'
    app=AppTest.from_string(script,default_timeout=30).run()
    assert not app.exception and len(app.get('link_button'))==4 and len(calls)==4
    old=AppTest.from_string('from denguepharma_analytics.reporting_ui import render\nrender("old",{"tables":{}},{})',default_timeout=30).run()
    assert not old.exception and old.info and not old.get('link_button')
    empty,_=analyze(data(snapshot,[]))
    app=AppTest.from_string('from denguepharma_analytics.reporting_ui import render\nrender("empty",'+repr({'tables':dict.fromkeys(tables)})+','+repr({'reporting':empty})+')',default_timeout=30).run()
    assert not app.exception and app.info and not app.get('link_button')


@pytest.mark.requirement('REQ-MIG-016')
def test_reporting_real_frozen_pilot_dates_match_manual_calendar_audit():
    if os.getenv('ANALYTICS_LIVE_POSTGRES')!='true':pytest.skip('Local pilot verification disabled')
    source=Path(__file__).resolve().parents[2]/'analytics/data/snapshots/sponsors-0.12/clinical-20.json'
    summary,tables=analyze(json.loads(source.read_bytes()));stats=summary['interval_summary']
    assert summary['trials']==10 and stats['completed']==8 and stats['observed']==5
    assert stats['min']==469 and stats['max']==1288 and stats['median']==709 and stats['q1']==709 and stats['q3']==725
    estimated=next(r for r in tables['reporting_registry'] if r['nct_id']=='NCT01728792')
    assert estimated['has_results'] is True and estimated['interval_days'] is None and 'RESULTS_TIPO_NAO_ACTUAL' in estimated['flags']
    assert sorted(r['interval_days'] for r in tables['reporting_registry'] if r['interval_days'] is not None)==[469,709,709,725,1288]
