"""Coleta completa por etapas curtas, com aprovacao congelada e retomada conservadora."""
from contextlib import contextmanager
from datetime import datetime
import json
import os
import tempfile
from pathlib import Path
from uuid import UUID
from zoneinfo import ZoneInfo

from .. import __version__
from ..domain import digest,json_bytes
from ..sources.snapshot import from_file
from .collection import Client
from .models import Principal
from .workspace import REVIEW_ROLES

ROLES=("PESQUISADOR","ADMINISTRADOR")
SAFE_RUN=("id","source","status","query","executed_at","finished_at","records_seen","total_returned","records_created","records_updated","records_unchanged","connector_version","api_version")


def plan(workspace,actor):
    actor.require(*REVIEW_ROLES)
    with workspace.transaction() as db:
        events=workspace.events(db); selection=workspace.selection_hash(db,events); blockers=[]
        if not set(actor.roles).intersection(ROLES):blockers.append("PAPEL_DE_PESQUISADOR_OU_ADMIN_NECESSARIO")
        try:workspace.require_current_selection(db,events,selection,calibrated=True)
        except ValueError as error:blockers.append(str(error))
        calibration=next((e for e in reversed(events) if e["kind"]=="CALIBRATION_APPROVED" and e["payload"]["basis_hash"]==selection),None)
        cutoff=workspace.input.data.get("protocol",{}).get("cutoff_date")
        try:
            if datetime.strptime(cutoff,"%Y-%m-%d").date()>datetime.now(ZoneInfo("America/Sao_Paulo")).date():blockers.append("FUTURE_CUTOFF")
        except (TypeError,ValueError):blockers.append("CALIBRATED_CUTOFF_REQUIRED")
        configuration=dict(schema_version="clinical-full-collection-1",workspace_id=workspace.key,pilot_input_hash=workspace.input.input_hash,clinical_protocol_hash=digest(json_bytes(workspace.protocol)),selection_hash=selection,
            calibration_event_id=calibration["id"] if calibration else None,cutoff=cutoff,strategy=dict(pubmed=dict(query=workspace.protocol["search"]["pubmed"]),clinicaltrials=dict(condition=workspace.protocol["search"]["clinicaltrials"]["condition"]),maxRecords=0),sources=["PUBMED","CLINICALTRIALS"])
        return dict(ready=not blockers,blockers=blockers,configuration=configuration,configuration_hash=digest(json_bytes(configuration)),
            notice="Plano de coleta, sem execucao ou publicacao. Corte e estrategia sao os calibrados; alterar criterios exige outra versao e aprovacao.")


@contextmanager
def lock(folder):
    with (folder/".runner.lock").open("a+b") as stream:
        stream.seek(0,2)
        if stream.tell()==0:stream.write(b"0");stream.flush()
        stream.seek(0)
        try:
            if os.name=="nt":
                import msvcrt
                msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:raise ValueError("COLLECTION_RUNNER_ALREADY_ACTIVE") from None
        try:yield
        finally:
            stream.seek(0)
            if os.name=="nt":msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(stream.fileno(),fcntl.LOCK_UN)


def save(path,state):
    temporary=path.with_suffix(".tmp")
    with temporary.open("wb") as stream:stream.write(json_bytes(state));stream.flush();os.fsync(stream.fileno())
    temporary.replace(path)


def immutable_write(path,content):
    """Publish a complete file atomically, without replacing a previous artifact."""
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent,prefix=".artifact-",delete=False) as stream:
            temporary=Path(stream.name)
            stream.write(content);stream.flush();os.fsync(stream.fileno())
        try:os.link(temporary,path)
        except FileExistsError:
            if path.read_bytes()!=content:raise ValueError("IMMUTABLE_COLLECTION_ARTIFACT") from None
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)


def advance(workspace,expected_collection,*,client=None,snapshot_loader=None,resume_failed=False,recover_id=None):
    # No diretorio/HTTP antes de verificar os pre-requisitos cientificos locais.
    local=plan(workspace,Principal("LOCAL_READ_ONLY_OPERATOR",("ADMINISTRADOR",)))
    if not local["ready"]:raise ValueError("FULL_COLLECTION_BLOCKED:"+",".join(local["blockers"]))
    config=local["configuration"]; config_hash=local["configuration_hash"]
    if expected_collection!=config_hash:raise ValueError("STALE_COLLECTION_PLAN")
    folder=(workspace.root/"collections"/config_hash).resolve();folder.mkdir(parents=True,exist_ok=True)
    with lock(folder):
        fresh=plan(workspace,Principal("LOCAL_READ_ONLY_OPERATOR",("ADMINISTRADOR",)))
        if not fresh["ready"] or fresh["configuration_hash"]!=config_hash:raise ValueError("STALE_COLLECTION_PLAN")
        path=folder/"checkpoint.json"
        if path.exists():
            state=json.loads(path.read_bytes())
            if state.get("configuration_hash")!=config_hash or state.get("configuration")!=config:raise ValueError("COLLECTION_CONFIGURATION_CHANGED_CREATE_NEW_FOLDER")
        else:
            if set(p.name for p in folder.iterdir())-{".runner.lock"}:raise ValueError("NEW_COLLECTION_FOLDER_REQUIRED")
            state=dict(configuration=config,configuration_hash=config_hash,code="CLINICAL-FULL-"+config_hash[:24],imports={},source_runs={},status="READY",pending=None)
            save(path,state)
        if state.get("status")=="SNAPSHOT_READY_PENDING_REVIEW":
            from_file(folder/"dataset.json",state["dataset_hash"])
            manifest=json.loads((folder/"manifest.json").read_bytes())
            if digest((folder/"manifest.json").read_bytes())!=state.get("manifest_hash") or manifest["configuration_hash"]!=config_hash or manifest["dataset_hash"]!=state["dataset_hash"]:raise ValueError("COLLECTION_MANIFEST_MISMATCH")
            return state
        client=client or Client()
        if not getattr(client,"token",None):client.login()
        me=client.call("/api/auth/me"); Principal(str(me["id"]),tuple(me["roles"])).require(*ROLES)
        state["operator_id"]=str(me["id"])
        def commit():save(path,state);return state
        def verify_protocol(row):
            if row.get("code")!=state["code"] or row.get("strategy")!=config["strategy"] or row.get("cutoffDate")!=config["cutoff"] or row.get("sources")!=config["sources"] or row.get("question")!=workspace.protocol["question"] or row.get("eligibility",{}).get("configurationHash")!=config_hash:raise ValueError("REMOTE_PROTOCOL_CONFIGURATION_MISMATCH")
        def attach(kind,row):
            identifier=str(UUID(str(row["id"])))
            if kind=="PROTOCOL":verify_protocol(row);state["protocol_id"]=identifier
            elif kind=="IMPORT":
                pending=state["pending"]
                if str(row.get("protocol_id"))!=state["protocol_id"] or row.get("source")!=pending["source"]:raise ValueError("REMOTE_IMPORT_MISMATCH")
                state["imports"][pending["source"]]=identifier
            state["pending"]=None;state["status"]="RECOVERED_REMOTE_ACTION"
        pending=state.get("pending")
        if pending:
            kind=pending["kind"]
            if kind=="PROTOCOL":
                candidates=[client.call("/api/protocols/"+str(UUID(recover_id)))] if recover_id else [p for p in client.call("/api/protocols") if p.get("code")==state["code"]]
                if len(candidates)==1:attach(kind,candidates[0]);return commit()
            elif kind=="IMPORT":
                candidates=[client.call("/api/imports/"+str(UUID(recover_id)))] if recover_id else [r for r in client.call("/api/imports") if str(r.get("protocol_id"))==state["protocol_id"] and r.get("source")==pending["source"]]
                if len(candidates)==1:attach(kind,candidates[0]);return commit()
            else:
                row=client.call(("/api/protocols/" if kind=="REGISTER" else "/api/imports/")+pending["id"])
                if (kind=="REGISTER" and row.get("status") in {"REGISTERED","FROZEN"}) or (kind=="RESUME" and row.get("status") in {"RUNNING","COMPLETED"}):
                    state["pending"]=None;state["status"]="RECOVERED_REMOTE_ACTION";return commit()
            state["status"]="REMOTE_ACTION_UNCONFIRMED";return commit()
        if recover_id:raise ValueError("RECOVERY_REQUIRES_PENDING_ACTION")
        def post(kind,url,body,pending_fields):
            fresh=plan(workspace,Principal("LOCAL_READ_ONLY_OPERATOR",("ADMINISTRADOR",)))
            if not fresh["ready"] or fresh["configuration_hash"]!=config_hash:raise ValueError("STALE_COLLECTION_PLAN")
            state["pending"]=dict(kind=kind,**pending_fields);state["status"]="DISPATCHING";commit()
            try:return client.call(url,body)
            except Exception:
                state["status"]="REMOTE_ACTION_UNCONFIRMED";commit();raise
        if "protocol_id" not in state:
            candidates=[p for p in client.call("/api/protocols") if p.get("code")==state["code"]]
            if candidates:
                state["pending"]=dict(kind="PROTOCOL")
                if len(candidates)==1:attach("PROTOCOL",candidates[0])
                else:state["status"]="REMOTE_ACTION_UNCONFIRMED"
                return commit()
            payload=dict(code=state["code"],title="Corpus clinico completo: dengue estabelecida",question=workspace.protocol["question"],sources=config["sources"],strategy=config["strategy"],cutoffDate=config["cutoff"],
                eligibility=dict(stage="COLETA_CLINICA_COMPLETA",configurationHash=config_hash,calibrationEventId=config["calibration_event_id"],selectionHash=config["selection_hash"],clinicalProtocolHash=config["clinical_protocol_hash"],selectionRequired=True))
            row=post("PROTOCOL","/api/protocols",payload,{})
            attach("PROTOCOL",row);return commit()
        remote=client.call("/api/protocols/"+state["protocol_id"]);verify_protocol(remote)
        if remote["status"]=="DRAFT":
            post("REGISTER","/api/protocols/"+state["protocol_id"]+"/register",{},dict(id=state["protocol_id"]))
            state["pending"]=None;state["status"]="PROTOCOL_REGISTERED";return commit()
        if remote["status"] not in {"REGISTERED","FROZEN"}:raise ValueError("REMOTE_PROTOCOL_NOT_REGISTERED")
        for source in config["sources"]:
            if source not in state["imports"]:
                candidates=[r for r in client.call("/api/imports") if str(r.get("protocol_id"))==state["protocol_id"] and r.get("source")==source]
                if candidates:
                    state["pending"]=dict(kind="IMPORT",source=source)
                    if len(candidates)==1:attach("IMPORT",candidates[0])
                    else:state["status"]="REMOTE_ACTION_UNCONFIRMED"
                    return commit()
                row=post("IMPORT","/api/imports",dict(protocolId=state["protocol_id"],source=source),dict(source=source))
                state["imports"][source]=str(UUID(str(row["runId"])));state["pending"]=None;state["status"]="IMPORT_STARTED";return commit()
            identifier=state["imports"][source];row=client.call("/api/imports/"+identifier)
            if str(row.get("protocol_id"))!=state["protocol_id"] or row.get("source")!=source:raise ValueError("REMOTE_IMPORT_MISMATCH")
            state["source_runs"][source]={k:row[k] for k in SAFE_RUN if k in row}
            if row["status"]=="FAILED" and resume_failed:
                post("RESUME","/api/imports/"+identifier+"/resume",{},dict(id=identifier))
                state["pending"]=None;state["status"]="IMPORT_RESUMED";return commit()
            if row["status"]!="COMPLETED":
                state["status"]="IMPORT_FAILED_RESUME_REQUIRED" if row["status"]=="FAILED" else "WAITING_IMPORT";return commit()
        dataset=folder/"dataset.json"
        if dataset.exists():
            snapshot=from_file(dataset)
            if snapshot.data["protocol"]["id"]!=state["protocol_id"]:raise ValueError("EXISTING_SNAPSHOT_PROTOCOL_MISMATCH")
        else:
            if snapshot_loader is None:
                from ..sources.collection_snapshot import snapshot_from_runs
                snapshot_loader=snapshot_from_runs
            snapshot=snapshot_loader(state["protocol_id"],list(state["imports"].values()))
            validate_snapshot(snapshot,state)
            immutable_write(dataset,snapshot.content)
        validate_snapshot(snapshot,state)
        manifest=dict(schema_version="clinical-full-result-1",collector_version=__version__,configuration=config,configuration_hash=config_hash,protocol_id=state["protocol_id"],imports=state["imports"],source_runs=state["source_runs"],dataset_hash=snapshot.input_hash,documents=len(snapshot.data["documents"]),published=False,clinical_reviews_transferred=False)
        content=json_bytes(manifest);manifest_path=folder/"manifest.json"
        immutable_write(manifest_path,content)
        state["dataset_hash"]=snapshot.input_hash;state["manifest_hash"]=digest(content);state["status"]="SNAPSHOT_READY_PENDING_REVIEW";return commit()


def validate_snapshot(snapshot,state):
    data=snapshot.data;protocol=data.get("protocol",{});runs=data.get("sourceRuns",[])
    if protocol.get("id")!=state["protocol_id"] or protocol.get("cutoff_date")!=state["configuration"]["cutoff"] or protocol.get("maxRecordsPerSource")!=0:raise ValueError("COLLECTION_SNAPSHOT_PROTOCOL_MISMATCH")
    if len(runs)!=len(state["imports"]) or {str(r.get("id")):r.get("source") for r in runs}!={identifier:source for source,identifier in state["imports"].items()} or any(r.get("status")!="COMPLETED" for r in runs):raise ValueError("COLLECTION_SNAPSHOT_RUN_MISMATCH")
    if data.get("studies") or data.get("scientificFields") or "clinical" in data:raise ValueError("METADATA_ONLY_SNAPSHOT_REQUIRED")
