"""Backup privado da curadoria e restauracao isolada; sem publicacao ou escrita no legado."""
from contextlib import closing
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
from tempfile import TemporaryDirectory
from zipfile import ZipFile,ZIP_DEFLATED,ZIP_STORED,BadZipFile

from .. import __version__
from ..domain import digest,json_bytes
from .workspace import Workspace,SCHEMA_SQL
from .full_collection import lock

FILES=("input.json","protocol.json","curation.sqlite3")
MAX_MEMBER=256*1024*1024
MAX_TOTAL=512*1024*1024
MAX_MANIFEST=64*1024


def file_hash(path):
    with path.open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()


def validate_manifest(manifest):
    if not isinstance(manifest,dict) or manifest.get("schema_version")!="clinical-private-backup-1":raise ValueError("BACKUP_MANIFEST_INVALID")
    for name in ("workspace_id","input_hash","protocol_hash","audit_head"):
        if not isinstance(manifest.get(name),str) or not re.fullmatch(r"[a-f0-9]{64}",manifest[name]):raise ValueError("BACKUP_MANIFEST_INVALID")
    if any(type(manifest.get(name)) is not int or manifest[name]<0 for name in ("events","sources")):raise ValueError("BACKUP_MANIFEST_INVALID")
    artifacts=manifest.get("artifacts")
    if not isinstance(artifacts,dict) or set(artifacts)!=set(FILES):raise ValueError("BACKUP_MANIFEST_INVALID")
    for item in artifacts.values():
        if not isinstance(item,dict) or type(item.get("size")) is not int or item["size"]<0 or not isinstance(item.get("sha256"),str) or not re.fullmatch(r"[a-f0-9]{64}",item["sha256"]):raise ValueError("BACKUP_MANIFEST_INVALID")


def read_only(path):
    db=sqlite3.connect(path.resolve().as_uri()+"?mode=ro",uri=True,timeout=30)
    db.row_factory=sqlite3.Row
    db.execute("PRAGMA query_only=ON");db.execute("PRAGMA trusted_schema=OFF")
    return db


def schema(db):
    # Indentacao externa ao SQL nao altera o contrato das tabelas e triggers.
    return [(r["type"],r["name"],r["tbl_name"]," ".join(r["sql"].split())) for r in db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type,name")]


def inspect(workspace):
    if any((workspace.folder/name).is_symlink() for name in FILES):raise ValueError("BACKUP_SYMLINK_SOURCE")
    with closing(sqlite3.connect(":memory:")) as expected:
        expected.row_factory=sqlite3.Row;expected.executescript(SCHEMA_SQL);expected_schema=schema(expected)
    with closing(read_only(workspace.folder/"curation.sqlite3")) as db:
        if schema(db)!=expected_schema:raise ValueError("UNSUPPORTED_CURATION_SCHEMA")
        if [r[0] for r in db.execute("PRAGMA integrity_check")]!=["ok"]:raise ValueError("CURATION_DATABASE_INTEGRITY")
        events=workspace.events(db)
        documents={d["documentId"]:d for d in workspace.input.data["documents"]}
        count=0
        for row in db.execute("SELECT * FROM sources"):
            document=documents.get(row["document_id"])
            if not document or not isinstance(row["text"],str) or digest(row["text"].encode())!=row["text_hash"] or row["content_hash"]!=document["contentHash"]:raise ValueError("BACKUP_SOURCE_INTEGRITY")
            if row["version_id"] not in {document["versionId"],document["versionId"]+":"+row["text_hash"][:16]}:raise ValueError("BACKUP_SOURCE_VERSION_MISMATCH")
            count+=1
        return dict(workspace_id=workspace.key,input_hash=workspace.input.input_hash,protocol_hash=digest(json_bytes(workspace.protocol)),
            audit_head=events[-1]["event_hash"] if events else "0"*64,events=len(events),sources=count)


def backup(workspace,output):
    output=Path(output).absolute()
    if output.exists() or output.is_symlink():raise ValueError("BACKUP_OUTPUT_EXISTS")
    if any((workspace.folder/name).is_symlink() for name in FILES):raise ValueError("BACKUP_SYMLINK_SOURCE")
    output.parent.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(dir=output.parent,prefix=".clinical-backup-") as temporary:
        stage=Path(temporary).resolve();assert stage.is_relative_to(output.parent.resolve())
        folder=stage/"clinical"/workspace.key;folder.mkdir(parents=True)
        # A reserva de escrita bloqueia novos votos/fontes durante a copia consistente.
        # Outra conexao somente leitura usa a API backup, incluindo paginas no WAL.
        with workspace.transaction():
            for name in FILES[:2]:(folder/name).write_bytes((workspace.folder/name).read_bytes())
            with closing(read_only(workspace.folder/"curation.sqlite3")) as source,closing(sqlite3.connect(folder/"curation.sqlite3")) as destination:
                source.backup(destination)
        details=inspect(Workspace(stage,workspace.key))
        artifacts={name:dict(sha256=file_hash(folder/name),size=(folder/name).stat().st_size) for name in FILES}
        if any(v["size"]>MAX_MEMBER for v in artifacts.values()) or sum(v["size"] for v in artifacts.values())>MAX_TOTAL:raise ValueError("BACKUP_SIZE_LIMIT")
        manifest=dict(schema_version="clinical-private-backup-1",software_version=__version__,created_at=datetime.now(timezone.utc).isoformat(),
            **details,artifacts=artifacts,private=True,encrypted=False,scope="clinical_workspace_only")
        archive=stage/"backup.zip"
        with ZipFile(archive,"w",compression=ZIP_DEFLATED) as stream:
            for name in FILES:stream.write(folder/name,arcname=name)
            stream.writestr("manifest.json",json_bytes(manifest))
        with archive.open("r+b") as stream:stream.flush();os.fsync(stream.fileno())
        try:os.link(archive,output)
        except FileExistsError:raise ValueError("BACKUP_OUTPUT_EXISTS") from None
        return dict(**details,archive=str(output),archive_hash=file_hash(output),bytes=output.stat().st_size,private=True)


def restore(archive,root,expected_hash):
    archive=Path(archive).resolve();root=Path(root).resolve()
    if not re.fullmatch(r"[a-f0-9]{64}",expected_hash or ""):raise ValueError("EXPECTED_BACKUP_HASH_REQUIRED")
    # Hash e ZIP sao lidos do mesmo descritor para evitar troca de arquivo entre etapas.
    with archive.open("rb") as raw:
        if hashlib.file_digest(raw,"sha256").hexdigest()!=expected_hash:raise ValueError("BACKUP_HASH_MISMATCH")
        raw.seek(0)
        try:
            with ZipFile(raw) as zipped:
                members=zipped.infolist()
                if len(members)!=4 or {m.filename for m in members}!=set(FILES)|{"manifest.json"}:raise ValueError("BACKUP_MEMBERS_INVALID")
                for member in members:
                    if member.is_dir() or stat.S_IFMT(member.external_attr>>16) not in {0,stat.S_IFREG} or member.flag_bits&1 or member.compress_type not in {ZIP_STORED,ZIP_DEFLATED}:raise ValueError("BACKUP_MEMBER_TYPE_INVALID")
                    if member.file_size>(MAX_MANIFEST if member.filename=="manifest.json" else MAX_MEMBER):raise ValueError("BACKUP_SIZE_LIMIT")
                if sum(m.file_size for m in members)>MAX_TOTAL+MAX_MANIFEST:raise ValueError("BACKUP_SIZE_LIMIT")
                manifest=json.loads(zipped.read("manifest.json"));validate_manifest(manifest);key=manifest["workspace_id"]
                target=root/"clinical"/key
                if not target.resolve().is_relative_to(root):raise ValueError("UNSAFE_RESTORE_TARGET")
                if target.exists() or target.is_symlink():raise ValueError("RESTORE_TARGET_EXISTS")
                root.mkdir(parents=True,exist_ok=True)
                with TemporaryDirectory(dir=root,prefix=".clinical-restore-") as temporary:
                    stage=Path(temporary).resolve();assert stage.is_relative_to(root)
                    folder=stage/"clinical"/key;folder.mkdir(parents=True)
                    for name in FILES:
                        info=zipped.getinfo(name);expected=manifest["artifacts"][name]
                        if expected.get("size")!=info.file_size:raise ValueError("BACKUP_MEMBER_SIZE_MISMATCH")
                        total=0;hash_=hashlib.sha256()
                        with zipped.open(name) as source,(folder/name).open("xb") as destination:
                            while chunk:=source.read(1024*1024):
                                total+=len(chunk)
                                if total>MAX_MEMBER:raise ValueError("BACKUP_SIZE_LIMIT")
                                hash_.update(chunk);destination.write(chunk)
                            destination.flush();os.fsync(destination.fileno())
                        if total!=expected["size"] or hash_.hexdigest()!=expected.get("sha256"):raise ValueError("BACKUP_MEMBER_HASH_MISMATCH")
                    details=inspect(Workspace(stage,key))
                    if any(manifest.get(k)!=v for k,v in details.items()):raise ValueError("BACKUP_MANIFEST_STATE_MISMATCH")
                    raw.seek(0)
                    if hashlib.file_digest(raw,"sha256").hexdigest()!=expected_hash:raise ValueError("BACKUP_HASH_CHANGED_DURING_RESTORE")
                    # Serializa restauracoes locais; nunca substitui workspace existente.
                    with lock(root):
                        if target.exists() or target.is_symlink():raise ValueError("RESTORE_TARGET_EXISTS")
                        target.parent.mkdir(parents=True,exist_ok=True)
                        folder.rename(target)
                    return dict(**details,archive_hash=expected_hash,restored_to=str(target),published=False)
        except (BadZipFile,json.JSONDecodeError,sqlite3.DatabaseError) as error:
            raise ValueError("INVALID_CLINICAL_BACKUP") from error
