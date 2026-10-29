import copy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient
from denguepharma_analytics.api import create_app
from denguepharma_analytics.analyses.sponsors import analyze,figures,MISSING,CONFLICT
from denguepharma_analytics.sources.collection_snapshot import safe_metadata
from denguepharma_analytics.sources.snapshot import load_snapshot
from denguepharma_analytics.domain import json_bytes,digest
from denguepharma_analytics.storage import export,publish


def trial(snapshot,key,nct='NCT00000001',name='Org A',kind='INDUSTRY'):
    doc=copy.deepcopy(snapshot.data['documents'][-1]);doc.update(documentId=key,versionId='v-'+key,contentHash=digest(key.encode()))
    section=doc['metadata']['protocolSection'];section['identificationModule']['nctId']=nct
    section['sponsorCollaboratorsModule']=dict(leadSponsor={'name':name,'class':kind,'email':'PRIVATE_CONTACT'},responsibleParty={'investigatorFullName':'PRIVATE_PERSON'})
    return doc


@pytest.mark.requirement('REQ-MIG-015')
def test_sponsors_known_counts_deduplicate_nct_and_keep_original_labels(snapshot):
    data=copy.deepcopy(snapshot.data)
    data['documents']=[trial(snapshot,'a'),trial(snapshot,'b',name=' org  a '),trial(snapshot,'c','NCT00000002','Org B','OTHER'),trial(snapshot,'d','NCT00000003',None,None)]
    summary,tables=analyze(data);assert summary['trials']==3 and summary['source_documents']==4
    rows=tables['corpus_sponsor_trials'];first=next(r for r in rows if r['nct_id']=='NCT00000001')
    assert first['sponsor_name']=='org a' and first['observed_names']==['Org A','org a'] and len(first['references'])==2
    counts={r['category']:r for r in summary['distributions'] if r['field']=='sponsor_type'}
    assert set(counts)=={'INDUSTRY','OTHER',MISSING} and all(r['count']==1 and r['denominator']==3 and r['proportion']==pytest.approx(1/3) for r in counts.values())
    assert summary['completeness'][0]['present']==2 and summary['completeness'][0]['missing']==1
    assert 'PRIVATE_' not in json.dumps(tables)


@pytest.mark.requirement('REQ-MIG-015')
def test_sponsors_conflicts_do_not_choose_latest_or_convert_to_absence(snapshot):
    data=copy.deepcopy(snapshot.data);data['documents']=[trial(snapshot,'a'),trial(snapshot,'b',name='Other sponsor',kind='OTHER')]
    data['documents'][1].update(version=99,retrievedAt='2026-10-28T12:00:00Z')
    summary,tables=analyze(data);row=tables['corpus_sponsor_trials'][0]
    assert row['sponsor_name'] is None and row['sponsor_type'] is None
    assert row['sponsor_name_status']==row['sponsor_type_status']=='CONFLITO'
    assert row['observed_types']==['INDUSTRY','OTHER'] and len(row['references'])==2
    assert all(r['category']==CONFLICT for r in summary['distributions'])
    assert all(r['conflicts']==1 and r['missing']==0 and r['proportion']==0 for r in summary['completeness'])
    data['documents'].append(trial(snapshot,'c',name=None,kind=None))
    _,tables=analyze(data);row=tables['corpus_sponsor_trials'][0]
    assert len(row['observations'])==3 and row['observations'][2]['sponsor_name_status']=='NAO_INFORMADO'
    assert row['sponsor_name_status']=='CONFLITO'


@pytest.mark.requirement('REQ-MIG-015')
def test_sponsors_absent_invalid_ids_empty_and_malformed_values(snapshot,tmp_path):
    data=copy.deepcopy(snapshot.data);data['documents']=[trial(snapshot,'a',None),trial(snapshot,'b','INVALID')]
    summary,_=analyze(data);assert summary['trials']==2 and summary['missing_nct']==summary['invalid_nct']==1
    malformed_id=copy.deepcopy(data);malformed_id['documents'][0]['metadata']['protocolSection']['identificationModule']['nctId']=0
    summary,_=analyze(malformed_id);assert summary['invalid_nct']==2 and summary['missing_nct']==0
    empty=copy.deepcopy(data);empty['documents']=[]
    summary,tables=analyze(empty);assert summary['trials']==0 and not tables['corpus_sponsor_trials']
    assert all(r['proportion'] is None and r['denominator']==0 for r in summary['completeness'])
    figures(summary,tmp_path/'figures');assert not (tmp_path/'figures').exists()
    bad=copy.deepcopy(data);bad['documents'][0]['metadata']['protocolSection']['sponsorCollaboratorsModule']['leadSponsor']['name']=123
    with pytest.raises(ValueError,match='SPONSOR_METADATA_INVALID'):analyze(bad)
    bad=copy.deepcopy(data);other=copy.deepcopy(bad['documents'][0]);other['metadata']['protocolSection']['identificationModule']['nctId']='NCT00000002';bad['documents'].append(other)
    with pytest.raises(ValueError,match='CONFLICTING_SPONSOR_DOCUMENT_IDENTITY'):analyze(bad)


@pytest.mark.requirement('REQ-MIG-015')
def test_sponsors_source_whitelist_excludes_contacts_investigators_and_text(snapshot):
    raw=trial(snapshot,'a')['metadata'];raw['abstract']='PRIVATE_ABSTRACT'
    section=raw['protocolSection'];section['contactsLocationsModule']={'locations':[{'country':'Brazil','email':'PRIVATE_EMAIL'}]}
    safe=safe_metadata(raw)
    assert safe['protocolSection']['sponsorCollaboratorsModule']=={'leadSponsor':{'name':'Org A','class':'INDUSTRY'}}
    assert 'PRIVATE_' not in json.dumps(safe)


@pytest.mark.requirement('REQ-MIG-015')
def test_sponsors_cli_api_parquet_png_and_quarto_use_same_frozen_input(snapshot,tmp_path):
    data=copy.deepcopy(snapshot.data);data['documents']=[trial(snapshot,'a')]
    content=json_bytes(data);path=tmp_path/'input.json';path.write_bytes(content)
    run=export(load_snapshot(content),tmp_path/'data');publish(tmp_path/'data',run['run_id'])
    command=[sys.executable,'-m','denguepharma_analytics.cli','--data-dir',str(tmp_path/'data'),'prepare','--input',str(path),'--expected-hash',digest(content)]
    done=subprocess.run(command,capture_output=True,text=True,timeout=40);assert done.returncode==0,done.stderr
    assert json.loads(done.stdout)['run_id']==run['run_id'] and len(run['tables'])==39
    app=TestClient(create_app(tmp_path/'data'));prefix='/api/public/analyses/'+run['run_id']
    assert app.get(prefix+'/summary').json()['sponsors']['trials']==1
    rows=app.get(prefix+'/tables/corpus_sponsor_trials').json()['rows'];assert rows[0]['sponsor_type']=='INDUSTRY'
    response=app.get(prefix+'/artifacts',params={'name':'figures/sponsors-types.png'})
    assert response.status_code==200 and digest(response.content)==run['artifacts']['figures/sponsors-types.png']
    assert 'PRIVATE_' not in json.dumps(rows)
    if os.getenv('QUARTO_BIN'):
        from denguepharma_analytics.reports.render import render
        render(tmp_path/'data',run['run_id'],os.environ['QUARTO_BIN'])
        html=app.get(prefix+'/artifacts',params={'name':'report.html'}).text
        assert 'Patrocinadores declarados nos registros' in html and 'INDUSTRY' in html


@pytest.mark.requirement('REQ-MIG-015')
def test_sponsors_metadata_addition_preserves_other_twenty_nine_tables(snapshot):
    from denguepharma_analytics.analyses.diagnostics import analyze as diagnostics
    from denguepharma_analytics.marts import build_tables
    old=snapshot.data;new=copy.deepcopy(old)
    new['documents'][-1]['metadata']['protocolSection']['sponsorCollaboratorsModule']={'leadSponsor':{'name':'Org A','class':'NIH'}}
    before=build_tables(old,*diagnostics(json_bytes(old)))
    after=build_tables(new,*diagnostics(json_bytes(new)))
    names=[n for n in before if not n.startswith(('corpus_sponsor_','reporting_','publication_reference_'))]
    assert len(names)==29 and all(before[n].equals(after[n]) for n in names)
    assert before['corpus_sponsor_trials'].to_pylist()!=after['corpus_sponsor_trials'].to_pylist()


@pytest.mark.requirement('REQ-MIG-015')
def test_sponsors_form_supports_old_and_empty_runs_and_public_tables(snapshot,monkeypatch):
    from streamlit.testing.v1 import AppTest
    from denguepharma_analytics import client
    summary,tables=analyze(snapshot.data);calls=[]
    monkeypatch.setattr(client,'table',lambda run,name,**kwargs:calls.append(name) or dict(rows=tables[name],total=len(tables[name])))
    script='from denguepharma_analytics.sponsors_ui import render\nrender("run",'+repr({'tables':dict.fromkeys(tables),'figures':{}})+','+repr({'sponsors':summary})+')'
    app=AppTest.from_string(script,default_timeout=30).run()
    assert not app.exception and len(app.get('link_button'))==3 and len(calls)==3
    old=AppTest.from_string('from denguepharma_analytics.sponsors_ui import render\nrender("old",{"tables":{}},{})',default_timeout=30).run()
    assert not old.exception and old.info and not old.get('link_button')
    empty,_=analyze({'documents':[]})
    empty_app=AppTest.from_string('from denguepharma_analytics.sponsors_ui import render\nrender("empty",'+repr({'tables':dict.fromkeys(tables)})+','+repr({'sponsors':empty})+')',default_timeout=30).run()
    assert not empty_app.exception and empty_app.info and not empty_app.get('link_button')


@pytest.mark.requirement('REQ-MIG-015')
def test_sponsors_live_metadata_snapshot_cli_preserves_exact_source_versions(tmp_path):
    if os.getenv('ANALYTICS_LIVE_POSTGRES')!='true':pytest.skip('PostgreSQL integration disabled')
    output=tmp_path/'snapshot.json'
    command=[sys.executable,'-m','denguepharma_analytics.cli','snapshot-collection','--protocol','c59fc9c6-32e4-4988-965e-5483692c1137','--run-id','ce7786e8-1758-46df-8fa6-c086cd4f2ffe','--run-id','5d50c7f2-0218-441f-870a-089c83f40238','--output',str(output)]
    done=subprocess.run(command,capture_output=True,text=True,timeout=30);assert done.returncode==0,done.stderr
    raw=output.read_bytes();data=load_snapshot(raw).data
    old=json.loads((Path(__file__).resolve().parents[2]/'analytics/data/calibration/clinical-001/dataset.json').read_bytes())
    assert {d['versionId']:d['contentHash'] for d in data['documents']}=={d['versionId']:d['contentHash'] for d in old['documents']}
    assert len(data['documents'])==20 and data['studies']==[] and data['scientificFields']==[] and 'clinical' not in data
    summary,_=analyze(data);assert summary['trials']==10 and all(r['present']==10 for r in summary['completeness'])
    again=subprocess.run(command,capture_output=True,text=True,timeout=30)
    assert again.returncode!=0 and 'SNAPSHOT_OUTPUT_EXISTS' in again.stderr and output.read_bytes()==raw
