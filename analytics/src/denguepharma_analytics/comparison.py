"""Comparacao reproduzivel de execucoes publicadas, sem inferencia clinica."""
import csv
from io import StringIO
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from . import __version__
from .domain import digest,json_bytes
from .marts import PUBLIC_TABLES
from .sources.snapshot import from_file
from .storage import require_published,code_hash

VERSION="published-comparison-1"
KINDS=("NOVO","NAO_OBSERVADO","CONTEUDO_ALTERADO","REFERENCIA_ALTERADA","REPRESENTACAO_ALTERADA","DATA_RECUPERACAO_ALTERADA","INALTERADO")
REFERENCE_FIELDS=("versionId","version","source","documentType","license","accessStatus")
DOCUMENT_COLUMNS=("document_id","change_kind","changed_fields","previous_title","current_title","previous_version_id","current_version_id","previous_content_hash","current_content_hash")
TABLE_COLUMNS=("table","status","previous_rows","current_rows","schema_changed","data_changed","previous_logical_hash","current_logical_hash")


def scope(data):
    protocol=data.get("protocol") or {}
    if not protocol.get("id"):raise ValueError("COMPARISON_PROTOCOL_REQUIRED")
    return dict(schema=data["schemaVersion"],dictionary=data["dictionaryVersion"],
        protocol={k:protocol.get(k) for k in ("id","code","version","cutoff_date","maxRecordsPerSource")},filters=data.get("filters"),
        searches=sorted({(r.get("source") or "",r.get("query") or "") for r in data.get("sourceRuns",[])}),
        clinical_protocol_hash=(data.get("clinical") or {}).get("protocol_hash"))


def index(data):
    documents={}
    for doc in data["documents"]:
        key=doc["documentId"]
        if key in documents and documents[key]!=doc:raise ValueError("AMBIGUOUS_COMPARISON_DOCUMENT")
        documents[key]=doc
    return documents


def compare(root,baseline,current):
    root=Path(root).resolve()
    manifests=[require_published(root,key) for key in (baseline,current)]
    snapshots=[from_file(root/"bronze"/m["input_hash"]/"snapshot.json",m["input_hash"]) for m in manifests]
    scopes=[scope(s.data) for s in snapshots]
    different=[k for k in scopes[0] if scopes[0][k]!=scopes[1][k]]
    if different:raise ValueError("INCOMPATIBLE_COMPARISON:"+",".join(different))
    before,after=[index(s.data) for s in snapshots];shared=set(before)&set(after)
    counts={k:0 for k in KINDS};changes=[]
    for key in sorted(set(before)|set(after)):
        old=before.get(key);new=after.get(key);fields=[]
        if old is None:kind="NOVO"
        elif new is None:kind="NAO_OBSERVADO"
        else:
            for field in ("contentHash",*REFERENCE_FIELDS,"title","metadata","studyLinks","retrievedAt"):
                if old.get(field)!=new.get(field):fields.append(field)
            kind="CONTEUDO_ALTERADO" if "contentHash" in fields else "REFERENCIA_ALTERADA" if set(fields)&set(REFERENCE_FIELDS) else "REPRESENTACAO_ALTERADA" if set(fields)&{"title","metadata","studyLinks"} else "DATA_RECUPERACAO_ALTERADA" if fields else "INALTERADO"
        counts[kind]+=1
        if kind=="INALTERADO":continue
        changes.append(dict(document_id=key,change_kind=kind,changed_fields=",".join(fields),
            previous_title=(old or {}).get("title"),current_title=(new or {}).get("title"),
            previous_version_id=(old or {}).get("versionId"),current_version_id=(new or {}).get("versionId"),
            previous_content_hash=(old or {}).get("contentHash"),current_content_hash=(new or {}).get("contentHash")))
    tables=[]
    old_tables,new_tables=[m["tables"] for m in manifests]
    for name in sorted((set(old_tables)|set(new_tables))&PUBLIC_TABLES):
        old=old_tables.get(name);new=new_tables.get(name)
        schema_changed=old["schema"]!=new["schema"] if old and new else None
        data_changed=old["logical_hash"]!=new["logical_hash"] if old and new else None
        status="TABELA_NOVA" if old is None else "TABELA_NAO_PRESENTE" if new is None else "SCHEMA_ALTERADO" if schema_changed else "DADOS_ALTERADOS" if data_changed else "INALTERADA"
        tables.append(dict(table=name,status=status,previous_rows=old["rows"] if old else None,current_rows=new["rows"] if new else None,
            schema_changed=schema_changed,data_changed=data_changed,previous_logical_hash=old["logical_hash"] if old else None,current_logical_hash=new["logical_hash"] if new else None))
    configuration=dict(schema_version=VERSION,software_version=__version__,code_hash=code_hash(),baseline=baseline,current=current,
        baseline_input_hash=snapshots[0].input_hash,current_input_hash=snapshots[1].input_hash,
        baseline_manifest_hash=digest((root/"runs"/baseline/"manifest.json").read_bytes()),current_manifest_hash=digest((root/"runs"/current/"manifest.json").read_bytes()))
    metrics=[]
    for kind in KINDS:
        denominator=len(after) if kind=="NOVO" else len(before) if kind=="NAO_OBSERVADO" else len(shared)
        metrics.append(dict(change_kind=kind,count=counts[kind],denominator=denominator,
            proportion=counts[kind]/denominator if denominator else None,unit="documento_de_origem_por_documentId"))
    return dict(comparison_id=digest(json_bytes(configuration)),configuration=configuration,comparable=True,
        baseline_documents=len(before),current_documents=len(after),shared_documents=len(shared),counts=counts,metrics=metrics,
        document_changes=changes,table_changes=tables,same_input=snapshots[0].input_hash==snapshots[1].input_hash,
        source_versions=sorted({m["version"] for m in manifests}),
        notice="Documentos por ID persistido, sem correspondencia aproximada. Nao observado nao significa exclusao, retratacao ou ausencia na literatura. Alteracao de conteudo nao demonstra mudanca de efeito clinico; mudanca de software nao equivale a nova evidencia.")


def csv_bytes(rows,columns):
    stream=StringIO(newline="");writer=csv.DictWriter(stream,fieldnames=columns,lineterminator="\n");writer.writeheader()
    for row in rows:
        writer.writerow({k:"'"+v if isinstance(v,str) and v.startswith(("=","+","-","@","\t","\r")) else v for k,v in row.items()})
    return stream.getvalue().encode("utf-8")


def artifacts(result):
    files={"comparison.json":json_bytes(result),"document_changes.csv":csv_bytes(result["document_changes"],DOCUMENT_COLUMNS),"table_changes.csv":csv_bytes(result["table_changes"],TABLE_COLUMNS)}
    manifest=dict(schema_version="comparison-artifacts-1",comparison_id=result["comparison_id"],configuration=result["configuration"],artifacts={name:digest(content) for name,content in files.items()})
    files["manifest.json"]=json_bytes(manifest)
    return files


def export(result,output):
    output=Path(output).resolve();files=artifacts(result)
    if output.exists():
        if not output.is_dir() or {p.name for p in output.iterdir()}!=set(files) or any(not (output/name).is_file() or (output/name).read_bytes()!=content for name,content in files.items()):raise ValueError("IMMUTABLE_COMPARISON_DIRECTORY")
        return dict(comparison_id=result["comparison_id"],output=str(output),reused=True)
    output.parent.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(dir=output.parent,prefix=".comparison-") as temporary:
        stage=Path(temporary).resolve();assert stage.is_relative_to(output.parent)
        # Move apenas a subpasta completa; o contexto limpa somente seu temporario.
        package=stage/"package";package.mkdir()
        for name,content in files.items():
            with (package/name).open("xb") as stream:stream.write(content);stream.flush();os.fsync(stream.fileno())
        if output.exists():raise ValueError("IMMUTABLE_COMPARISON_DIRECTORY")
        package.rename(output)
    return dict(comparison_id=result["comparison_id"],output=str(output),reused=False)
