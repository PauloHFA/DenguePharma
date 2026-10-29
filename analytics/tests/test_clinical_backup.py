import json
from contextlib import nullcontext
from pathlib import Path
import sqlite3
import subprocess
import sys
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED

import pytest
from test_clinical import workspace,include,complete_calibration,approve,result,R1,ADJ
from denguepharma_analytics.clinical import backup as module
from denguepharma_analytics.clinical.backup import backup,restore,inspect,file_hash
from denguepharma_analytics.clinical.workspace import Workspace
from denguepharma_analytics.domain import digest,json_bytes


def populated(workspace):
    include(workspace);complete_calibration(workspace);approve(workspace,result(workspace))


def repack(original,target,*,mutate_db=None,mutate_manifest=None,extra=None):
    with ZipFile(original) as zipped:files={n:zipped.read(n) for n in zipped.namelist()}
    manifest=json.loads(files['manifest.json'])
    if mutate_db:
        dbpath=target.with_suffix('.sqlite3');dbpath.write_bytes(files['curation.sqlite3'])
        with sqlite3.connect(dbpath) as db:mutate_db(db)
        files['curation.sqlite3']=dbpath.read_bytes()
        manifest['artifacts']['curation.sqlite3']=dict(size=len(files['curation.sqlite3']),sha256=digest(files['curation.sqlite3']))
    if mutate_manifest:mutate_manifest(manifest)
    files['manifest.json']=json_bytes(manifest)
    with ZipFile(target,'w',ZIP_DEFLATED) as zipped:
        for name,data in files.items():zipped.writestr(name,data)
        if extra:zipped.writestr(*extra)
    return file_hash(target)


@pytest.mark.requirement('REQ-MIG-013')
def test_private_backup_restores_votes_sources_results_and_wal(workspace,tmp_path):
    populated(workspace);before=workspace.snapshot();original=inspect(workspace)
    # Keep a WAL connection open: copying only the .sqlite3 file would miss pages.
    with sqlite3.connect(workspace.folder/'curation.sqlite3') as wal:
        wal.execute('PRAGMA journal_mode=WAL')
        document=next(d for d in workspace.input.data['documents'] if d['documentId']=='t1')
        workspace.attach_source(document,'Updated permitted representation for WAL test')
        before=workspace.snapshot();original=inspect(workspace)
        (workspace.root/'.env').write_text('TEST_PRIVATE_PASSWORD_SHOULD_NOT_BE_PACKAGED')
        saved=backup(workspace,tmp_path/'private.zip')
    assert saved['events']==8 and original['sources']==4
    assert workspace.snapshot().input_hash==before.input_hash
    with ZipFile(saved['archive']) as zipped:
        assert set(zipped.namelist())==set(module.FILES)|{'manifest.json'}
        assert b'TEST_PRIVATE_PASSWORD' not in b''.join(zipped.read(n) for n in zipped.namelist())
        assert json.loads(zipped.read('manifest.json'))['private'] is True
    restored=restore(Path(saved['archive']),tmp_path/'isolated',saved['archive_hash'])
    other=Workspace(tmp_path/'isolated',workspace.key)
    assert inspect(other)==original and other.snapshot().input_hash==before.input_hash
    assert other.private_state(R1)==workspace.private_state(R1)
    assert len(other.freeze()['results'])==1
    assert restored['published'] is False and not (tmp_path/'isolated'/'publications').exists()
    with sqlite3.connect(other.folder/'curation.sqlite3') as db:
        with pytest.raises(sqlite3.IntegrityError,match='append-only'):db.execute('DELETE FROM events')


@pytest.mark.requirement('REQ-MIG-013')
def test_private_backup_requires_trusted_hash_and_verifies_members(workspace,tmp_path):
    saved=backup(workspace,tmp_path/'private.zip');target=tmp_path/'target'
    with pytest.raises(ValueError,match='HASH_REQUIRED'):restore(Path(saved['archive']),target,None)
    with pytest.raises(ValueError,match='HASH_MISMATCH'):restore(Path(saved['archive']),target,'f'*64)
    assert not target.exists()
    bad=tmp_path/'tampered.zip'
    hash_=repack(saved['archive'],bad,mutate_manifest=lambda m:m['artifacts']['input.json'].update(sha256='a'*64))
    with pytest.raises(ValueError,match='MEMBER_HASH'):restore(bad,target,hash_)
    assert not (target/'clinical').exists() and not list(target.glob('.clinical-restore-*'))


@pytest.mark.requirement('REQ-MIG-013')
def test_private_restore_rejects_paths_duplicates_and_symlink_entries(workspace,tmp_path):
    saved=backup(workspace,tmp_path/'private.zip');target=tmp_path/'target'
    for index,name in enumerate(('../outside.txt','/absolute.txt','input.json')):
        bad=tmp_path/f'extra{index}.zip'
        with pytest.warns(UserWarning) if name=='input.json' else nullcontext():
            hash_=repack(saved['archive'],bad,extra=(name,b'UNTRUSTED'))
        with pytest.raises(ValueError,match='MEMBERS'):restore(bad,target,hash_)
    with ZipFile(saved['archive']) as zipped:files={n:zipped.read(n) for n in zipped.namelist()}
    bad=tmp_path/'symlink.zip'
    with ZipFile(bad,'w') as zipped:
        for name,data in files.items():
            info=ZipInfo(name);info.external_attr=((0o120777 if name=='input.json' else 0o100600)<<16)
            zipped.writestr(info,data)
    with pytest.raises(ValueError,match='TYPE'):restore(bad,target,file_hash(bad))
    assert not target.exists() and not (tmp_path/'outside.txt').exists()


@pytest.mark.requirement('REQ-MIG-013')
def test_private_restore_checks_schema_audit_chain_and_source_hashes(workspace,tmp_path):
    populated(workspace);saved=backup(workspace,tmp_path/'private.zip')
    def edit(db,table,sql):
        trigger=table+'_no_update'
        original=db.execute('SELECT sql FROM sqlite_master WHERE name=?',(trigger,)).fetchone()[0]
        db.execute('DROP TRIGGER '+trigger);db.execute(sql);db.execute(original)
    cases=[('schema',lambda db:db.execute('DROP TRIGGER events_no_delete'),'SCHEMA'),
        ('audit',lambda db:edit(db,'events',"UPDATE events SET event_hash='forged' WHERE seq=1"),'AUDIT_CHAIN'),
        ('source',lambda db:edit(db,'sources',"UPDATE sources SET text='forged text'"),'SOURCE_INTEGRITY')]
    for label,mutator,error in cases:
        bad=tmp_path/(label+'.zip');hash_=repack(saved['archive'],bad,mutate_db=mutator)
        with pytest.raises(ValueError,match=error):restore(bad,tmp_path/(label+'-root'),hash_)
        assert not (tmp_path/(label+'-root')/'clinical').exists()


@pytest.mark.requirement('REQ-MIG-013')
def test_private_backup_and_restore_never_overwrite_existing_files(workspace,tmp_path,monkeypatch):
    output=tmp_path/'private.zip';saved=backup(workspace,output);before=output.read_bytes()
    with pytest.raises(ValueError,match='OUTPUT_EXISTS'):backup(workspace,output)
    assert output.read_bytes()==before
    # The actual source is an existing target; it must not be replaced.
    frozen=workspace.snapshot().input_hash
    with pytest.raises(ValueError,match='TARGET_EXISTS'):restore(output,workspace.root,saved['archive_hash'])
    assert workspace.snapshot().input_hash==frozen
    other=tmp_path/'other';restore(output,other,saved['archive_hash'])
    sentinel=other/'clinical'/workspace.key/'keep.txt';sentinel.write_text('preserve')
    with pytest.raises(ValueError,match='TARGET_EXISTS'):restore(output,other,saved['archive_hash'])
    assert sentinel.read_text()=='preserve'
    with monkeypatch.context() as patch:
        patch.setattr(module.os,'link',lambda *args: (_ for _ in ()).throw(OSError('simulated disk failure')))
        with pytest.raises(OSError):backup(workspace,tmp_path/'unfinished.zip')
    assert not (tmp_path/'unfinished.zip').exists() and not list(tmp_path.glob('.clinical-backup-*'))
    assert workspace.snapshot().input_hash==frozen


@pytest.mark.requirement('REQ-MIG-013')
def test_private_restore_enforces_size_and_manifest_state(workspace,tmp_path,monkeypatch):
    saved=backup(workspace,tmp_path/'private.zip');target=tmp_path/'target'
    with monkeypatch.context() as patch:
        patch.setattr(module,'MAX_MEMBER',1)
        with pytest.raises(ValueError,match='SIZE_LIMIT'):restore(Path(saved['archive']),target,saved['archive_hash'])
    assert not target.exists()
    bad=tmp_path/'state.zip';hash_=repack(saved['archive'],bad,mutate_manifest=lambda m:m.update(events=100))
    with pytest.raises(ValueError,match='MANIFEST_STATE'):restore(bad,target,hash_)
    assert not (target/'clinical').exists()
    malformed=tmp_path/'malformed.zip'
    hash_=repack(saved['archive'],malformed,mutate_manifest=lambda m:m.update(artifacts=[]))
    with pytest.raises(ValueError,match='MANIFEST_INVALID'):restore(malformed,target,hash_)


@pytest.mark.requirement('REQ-MIG-013')
def test_private_restore_detects_archive_change_before_install(workspace,tmp_path,monkeypatch):
    output=tmp_path/'private.zip';saved=backup(workspace,output);target=tmp_path/'target'
    original_inspect=module.inspect
    def changed_archive(current):
        details=original_inspect(current)
        with output.open('ab') as stream:stream.write(b'changed after validation')
        return details
    monkeypatch.setattr(module,'inspect',changed_archive)
    with pytest.raises(ValueError,match='HASH_CHANGED'):restore(output,target,saved['archive_hash'])
    assert not (target/'clinical').exists() and not list(target.glob('.clinical-restore-*'))


@pytest.mark.requirement('REQ-MIG-013')
def test_private_backup_cli_roundtrip_and_required_hash(workspace,tmp_path):
    populated(workspace)
    base=[sys.executable,'-m','denguepharma_analytics.cli']
    command=base+['--data-dir',str(workspace.root),'clinical-backup','--workspace',workspace.key,'--output',str(tmp_path/'cli.zip')]
    result_=subprocess.run(command,capture_output=True,text=True,timeout=30)
    assert result_.returncode==0,result_.stderr
    saved=json.loads(result_.stdout)
    assert R1.id not in result_.stdout and 'quote' not in result_.stdout
    command=base+['--data-dir',str(tmp_path/'isolated'),'clinical-restore','--input',saved['archive']]
    missing=subprocess.run(command,capture_output=True,text=True,timeout=30)
    assert missing.returncode!=0 and '--expected-hash' in missing.stderr
    done=subprocess.run(command+['--expected-hash',saved['archive_hash']],capture_output=True,text=True,timeout=30)
    assert done.returncode==0,done.stderr
    assert json.loads(done.stdout)['events']==8
    assert Workspace(tmp_path/'isolated',workspace.key).snapshot().input_hash==workspace.snapshot().input_hash
