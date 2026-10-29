import copy
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from test_clinical import workspace,R1,ADJ,include,complete_calibration,screen
from denguepharma_analytics.api import create_app
from denguepharma_analytics.clinical.full_collection import plan,advance,lock,immutable_write
from denguepharma_analytics.clinical.models import Principal
from denguepharma_analytics.sources.collection_snapshot import safe_metadata,snapshot_from_runs
from denguepharma_analytics.sources.snapshot import load_snapshot
from denguepharma_analytics.domain import json_bytes


class Remote:
    def __init__(self):self.token=None;self.protocols={};self.imports={};self.posts=[];self.lost=None;self.roles=["ADMINISTRADOR"]
    def login(self):self.token="TEST_TOKEN_NEVER_PERSIST"
    def call(self,path,body=None,binary=False):
        if path=="/api/auth/me":return dict(id="test-operator",roles=self.roles)
        if body is not None:self.posts.append((path,copy.deepcopy(body)))
        if path=="/api/protocols":
            if body is None:return list(self.protocols.values())
            identifier=str(uuid4());row=dict(body,id=identifier,status="DRAFT");self.protocols[identifier]=row
            if self.lost=="PROTOCOL":self.lost=None;raise TimeoutError("Simulated lost response")
            return copy.deepcopy(row)
        if path.startswith("/api/protocols/"):
            identifier=path.split('/')[3];row=self.protocols[identifier]
            if path.endswith('/register'):row['status']='REGISTERED'
            return copy.deepcopy(row)
        if path=="/api/imports":
            if body is None:return list(self.imports.values())
            identifier=str(uuid4());self.imports[identifier]=dict(id=identifier,protocol_id=body['protocolId'],source=body['source'],status='COMPLETED',records_seen=2,total_returned=2,params='PRIVATE_KEY',last_error='PRIVATE_SECRET')
            if self.lost=="IMPORT":self.lost=None;raise TimeoutError("Simulated lost response")
            return dict(runId=identifier)
        if path.startswith("/api/imports/"):
            identifier=path.split('/')[3];row=self.imports[identifier]
            if path.endswith('/resume'):row['status']='COMPLETED';return dict(runId=identifier)
            return copy.deepcopy(row)
        raise AssertionError(path)


def calibrated(workspace):
    include(workspace);complete_calibration(workspace)
    return plan(workspace,ADJ)['configuration_hash']


def loader(remote,snapshot,*,bad=False):
    def load(protocol_id,ids):
        data=copy.deepcopy(snapshot.data);p=remote.protocols[protocol_id]
        data['protocol']=dict(id=protocol_id,code=p['code'],version=1,cutoff_date=p['cutoffDate'],maxRecordsPerSource=0)
        data['sourceRuns']=[{k:remote.imports[i][k] for k in ('id','source','status','records_seen','total_returned')} for i in ids]
        if bad:data['clinical']={'forged':'not allowed'}
        return load_snapshot(json_bytes(data))
    return load


def finish(workspace,identifier,remote,snapshot):
    for _ in range(12):
        state=advance(workspace,identifier,client=remote,snapshot_loader=loader(remote,snapshot))
        if state['status']=='SNAPSHOT_READY_PENDING_REVIEW':return state
    raise AssertionError('Collection did not finish')


@pytest.mark.requirement("REQ-CLN-011")
def test_full_collection_blocked_before_files_or_network(workspace,tmp_path):
    class NoNetwork:
        def login(self):raise AssertionError('must not authenticate')
        def call(self,*args,**kwargs):raise AssertionError('must not contact remote')
    before=workspace.snapshot().input_hash
    assert not plan(workspace,ADJ)['ready']
    with pytest.raises(ValueError,match='FULL_COLLECTION_BLOCKED'):advance(workspace,'a'*64,client=NoNetwork())
    assert not (workspace.root/'collections').exists() and workspace.snapshot().input_hash==before


@pytest.mark.requirement("REQ-CLN-011")
def test_full_collection_frozen_protocol_snapshot_and_idempotent_completion(workspace,snapshot,monkeypatch):
    identifier=calibrated(workspace);remote=Remote();state=finish(workspace,identifier,remote,snapshot)
    assert len(remote.protocols)==1 and len(remote.imports)==2
    protocol=next(iter(remote.protocols.values()))
    assert protocol['strategy']['maxRecords']==0 and protocol['strategy']['pubmed']['query']==workspace.protocol['search']['pubmed']
    assert protocol['cutoffDate']==workspace.input.data['protocol']['cutoff_date']
    count=len(remote.posts);assert advance(workspace,identifier,client=remote)==state and len(remote.posts)==count
    folder=workspace.root/'collections'/identifier
    all_state=(folder/'checkpoint.json').read_text()+(folder/'manifest.json').read_text()
    assert 'PRIVATE_SECRET' not in all_state and 'PRIVATE_KEY' not in all_state and 'TEST_TOKEN' not in all_state
    assert json.loads((folder/'manifest.json').read_bytes())['published'] is False
    artifact=folder/'atomic-test.json'
    with monkeypatch.context() as patch:
        patch.setattr(os,'link',lambda *args: (_ for _ in ()).throw(OSError('interrupted before publication')))
        with pytest.raises(OSError):immutable_write(artifact,b'complete')
    assert not artifact.exists() and not list(folder.glob('.artifact-*'))
    immutable_write(artifact,b'complete');immutable_write(artifact,b'complete')
    with pytest.raises(ValueError,match='IMMUTABLE'):immutable_write(artifact,b'changed')
    assert artifact.read_bytes()==b'complete'
    with pytest.raises(ValueError,match='MANIFEST_MISMATCH'):
        (folder/'manifest.json').write_text('{}');advance(workspace,identifier,client=remote)


@pytest.mark.requirement("REQ-CLN-011")
def test_lost_responses_reconcile_without_duplicate_post(workspace,snapshot):
    identifier=calibrated(workspace);remote=Remote();remote.lost='PROTOCOL'
    with pytest.raises(TimeoutError):advance(workspace,identifier,client=remote)
    assert len(remote.protocols)==1
    assert advance(workspace,identifier,client=remote)['status']=='RECOVERED_REMOTE_ACTION'
    advance(workspace,identifier,client=remote) # register known protocol
    remote.lost='IMPORT'
    with pytest.raises(TimeoutError):advance(workspace,identifier,client=remote)
    assert advance(workspace,identifier,client=remote)['status']=='RECOVERED_REMOTE_ACTION'
    finish(workspace,identifier,remote,snapshot)
    assert len(remote.protocols)==1 and len(remote.imports)==2
    assert sum(p=='/api/imports' for p,_ in remote.posts)==2


@pytest.mark.requirement("REQ-CLN-011")
def test_failed_import_resumes_existing_id_and_changed_calibration_blocks(workspace,snapshot):
    identifier=calibrated(workspace);remote=Remote()
    for _ in range(3):advance(workspace,identifier,client=remote)
    run=next(iter(remote.imports.values()));run['status']='FAILED'
    assert advance(workspace,identifier,client=remote)['status']=='IMPORT_FAILED_RESUME_REQUIRED'
    assert len(remote.imports)==1
    assert advance(workspace,identifier,client=remote,resume_failed=True)['status']=='IMPORT_RESUMED'
    assert len(remote.imports)==1 and any(p.endswith('/'+run['id']+'/resume') for p,_ in remote.posts)
    finish(workspace,identifier,remote,snapshot)
    screen(workspace,R1) # New selection hash invalidates the calibration, even after collection.
    count=len(remote.posts)
    with pytest.raises(ValueError,match='BLOCKED'):advance(workspace,identifier,client=remote)
    assert len(remote.posts)==count


@pytest.mark.requirement("REQ-CLN-011")
def test_collection_ambiguous_pending_is_not_reposted_and_roles_are_checked(workspace):
    identifier=calibrated(workspace);remote=Remote();remote.lost='PROTOCOL'
    with pytest.raises(TimeoutError):advance(workspace,identifier,client=remote)
    remote.protocols.clear();count=len(remote.posts)
    assert advance(workspace,identifier,client=remote)['status']=='REMOTE_ACTION_UNCONFIRMED'
    assert len(remote.posts)==count
    remote.roles=['LEITOR']
    with pytest.raises(PermissionError):advance(workspace,identifier,client=remote)
    with pytest.raises(ValueError,match='STALE_COLLECTION_PLAN'):advance(workspace,'f'*64,client=remote)
    folder=workspace.root/'collections'/identifier
    with lock(folder):
        with pytest.raises(ValueError,match='ALREADY_ACTIVE'):advance(workspace,identifier,client=remote)


@pytest.mark.requirement("REQ-CLN-011")
def test_metadata_snapshot_rejects_transferred_reviews_and_sanitizes(workspace,snapshot):
    identifier=calibrated(workspace);remote=Remote()
    for _ in range(4):advance(workspace,identifier,client=remote)
    with pytest.raises(ValueError,match='METADATA_ONLY'):advance(workspace,identifier,client=remote,snapshot_loader=loader(remote,snapshot,bad=True))
    assert not (workspace.root/'collections'/identifier/'dataset.json').exists()
    finish(workspace,identifier,remote,snapshot)
    metadata=safe_metadata(dict(title='private title',abstract='PRIVATE_TEXT',contacts='PRIVATE_CONTACT',pmid='123',protocolSection=dict(contactsLocationsModule=dict(locations=[dict(country='Brazil',email='PRIVATE_EMAIL')]),armsInterventionsModule=dict(interventions=[dict(type='DRUG',name='A',description='PRIVATE_DESCRIPTION')]))))
    assert 'PRIVATE_' not in json.dumps(metadata) and metadata['protocolSection']['contactsLocationsModule']['locations']==[dict(country='Brazil')]


@pytest.mark.requirement("REQ-CLN-011")
def test_plan_api_and_ui_are_readonly_and_pending_cli_is_blocked(workspace,tmp_path,monkeypatch):
    from streamlit.testing.v1 import AppTest
    from denguepharma_analytics import client
    app=TestClient(create_app(tmp_path,authenticate=lambda token:ADJ));path=f'/api/clinical/{workspace.key}/collection-plan'
    assert app.get(path).status_code==401
    state=app.get(path,headers={'Authorization':'Bearer token'}).json();assert not state['ready']
    monkeypatch.setattr(client,'private',lambda *args,**kwargs:state)
    ui=AppTest.from_string("from denguepharma_analytics.clinical.collection_ui import render\nrender('workspace','token')",default_timeout=30).run()
    assert not ui.exception and ui.warning and not ui.button
    result=subprocess.run([sys.executable,'-m','denguepharma_analytics.cli','--data-dir',str(tmp_path),'clinical-collect-full','--workspace',workspace.key,'--collection',state['configuration_hash']],capture_output=True,text=True,timeout=30)
    assert result.returncode!=0 and 'FULL_COLLECTION_BLOCKED' in result.stderr and not (workspace.root/'collections').exists()


@pytest.mark.requirement("REQ-CLN-011")
def test_live_collection_snapshot_readonly_preserves_pilot_versions():
    if os.getenv('ANALYTICS_LIVE_POSTGRES')!='true':pytest.skip('Local PostgreSQL verification disabled')
    from denguepharma_analytics.sources.postgres import load_env
    from denguepharma_analytics.preparation.documents import prepare
    load_env(Path(__file__).resolve().parents[2]/'.env')
    snapshot=snapshot_from_runs('c59fc9c6-32e4-4988-965e-5483692c1137',['ce7786e8-1758-46df-8fa6-c086cd4f2ffe','5d50c7f2-0218-441f-870a-089c83f40238'])
    old=json.loads((Path(__file__).resolve().parents[2]/'analytics/data/calibration/clinical-001/dataset.json').read_bytes())
    assert len(snapshot.data['documents'])==20 and snapshot.data['studies']==[] and snapshot.data['scientificFields']==[]
    assert {d['versionId']:d['contentHash'] for d in snapshot.data['documents']}=={d['versionId']:d['contentHash'] for d in old['documents']}
    assert len(prepare(snapshot.data)[0])==len(prepare(old)[0])==20
    assert all('abstract' not in d['metadata'] for d in snapshot.data['documents'])
