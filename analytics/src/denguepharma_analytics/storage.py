"""Runs imutaveis, bronze privado e publicacao local explicita. Sem escrita na base legada."""
from __future__ import annotations

from importlib.metadata import version
import json
import os
import platform
from pathlib import Path
import re
import shutil
import tempfile

import duckdb
import pyarrow.parquet as pq

from . import __version__
from .domain import digest, json_bytes
from .sources.snapshot import Snapshot
from .analyses.diagnostics import analyze
from .marts import build_tables, PUBLIC_TABLES, SCHEMAS


def default_root():
    return Path(os.environ.get("ANALYTICS_DATA_DIR", Path(__file__).resolve().parents[2] / "data")).resolve()


def code_hash():
    root = Path(__file__).parent
    return digest(b"".join(str(p.relative_to(root)).replace("\\", "/").encode()+b"\0"+p.read_bytes() for p in sorted(root.rglob("*.py"))))


def _safe_child(root, relative):
    target = (root / relative).resolve()
    if not target.is_relative_to(root.resolve()): raise ValueError("UNSAFE_ARTIFACT_PATH")
    return target


def run_path(root, run_id):
    if not re.fullmatch(r"[a-f0-9]{64}", run_id): raise ValueError("INVALID_RUN_ID")
    return _safe_child(root, "runs/" + run_id)


def verify_run(root: Path, run_id: str):
    folder = run_path(root, run_id)
    manifest = json.loads((folder / "manifest.json").read_bytes())
    if manifest.get("run_id") != run_id: raise ValueError("MANIFEST_RUN_MISMATCH")
    for name, expected in manifest["artifacts"].items():
        target = _safe_child(folder, name)
        if not target.is_file() or digest(target.read_bytes()) != expected: raise ValueError("ARTIFACT_HASH_MISMATCH:" + name)
    bronze = _safe_child(root, "bronze/" + manifest["input_hash"] + "/snapshot.json")
    if digest(bronze.read_bytes()) != manifest["input_hash"]: raise ValueError("BRONZE_HASH_MISMATCH")
    return manifest


def export(snapshot: Snapshot, root: Path):
    root = root.resolve(); root.mkdir(parents=True, exist_ok=True)
    dependencies = {name: version(name) for name in ("duckdb", "pyarrow", "pandas", "numpy", "scipy", "matplotlib")}
    dependencies["python"] = platform.python_version()
    configuration = {"version": __version__, "dictionary": "analytics-foundation-1", "code_hash": code_hash(),
                     "input_hash": snapshot.input_hash, "dependencies": dependencies}
    run_id = digest(json_bytes(configuration))
    destination = run_path(root, run_id)
    if destination.exists(): return verify_run(root, run_id)
    bronze = root / "bronze" / snapshot.input_hash
    bronze.mkdir(parents=True, exist_ok=True)
    try:
        with (bronze / "snapshot.json").open("xb") as stream: stream.write(snapshot.content)
    except FileExistsError:
        if (bronze / "snapshot.json").read_bytes() != snapshot.content: raise ValueError("BRONZE_HASH_MISMATCH")
    summary, records = analyze(snapshot.content)
    from .clinical.analysis import summary as clinical_summary, figures
    summary["clinical"] = clinical_summary(snapshot.data.get("clinical"))
    from .clinical.calibration import analyze as calibration_analysis, report as calibration_report, figures as calibration_figures
    summary["calibration"],_=calibration_analysis(snapshot.data,records)
    from .analyses.sponsors import analyze as sponsor_analysis,figures as sponsor_figures
    summary["sponsors"],_=sponsor_analysis(snapshot.data)
    from .analyses.reporting import analyze as reporting_analysis,figures as reporting_figures
    summary["reporting"],_=reporting_analysis(snapshot.data)
    from .analyses.publication_refs import analyze as publication_analysis,figures as publication_figures
    summary["publication_references"],_=publication_analysis(snapshot.data)
    tables = build_tables(snapshot.data, summary, records)
    stage = Path(tempfile.mkdtemp(prefix="analytics-", dir=root))
    try:
        (stage / "silver").mkdir(); (stage / "gold").mkdir()
        catalogue = {}
        with duckdb.connect(str(stage / "analytics.duckdb")) as db:
            for name, table in tables.items():
                layer = "silver" if name.startswith("silver_") else "gold"
                file = f"{layer}/{name}.parquet"
                pq.write_table(table, stage / file, compression="zstd", version="2.6", use_dictionary=False, write_statistics=True)
                db.register("incoming", table)
                db.execute(f'CREATE TABLE "{name}" AS SELECT * FROM incoming')
                db.unregister("incoming")
                catalogue[name] = {"file": file, "rows": table.num_rows, "public": name in PUBLIC_TABLES,
                    "schema": [{"name": f.name, "type": str(f.type)} for f in table.schema],
                    "logical_hash": digest(json_bytes(table.to_pylist()))}
            db.execute("CHECKPOINT")
        figures(snapshot.data.get("clinical"),stage/"figures")
        calibration_figures(summary["calibration"],stage/"figures")
        sponsor_figures(summary["sponsors"],stage/"figures")
        reporting_figures(summary["reporting"],stage/"figures")
        publication_figures(summary["publication_references"],stage/"figures")
        (stage/"research_findings.md").write_text(calibration_report(summary,snapshot.input_hash),encoding="utf-8",newline="\n")
        (stage / "summary.json").write_bytes(json_bytes(summary))
        # Regras/fonte analitica recuperaveis sem importar Java ou o pacote legado.
        package = Path(__file__).parent
        source_dir = stage / "reproduction_source"; source_dir.mkdir()
        for file in sorted(package.rglob("*.py")):
            target = source_dir / file.relative_to(package); target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(file.read_bytes())
        hashes = {str(file.relative_to(stage)).replace("\\", "/"): digest(file.read_bytes()) for file in sorted(stage.rglob("*")) if file.is_file()}
        manifest = {"schema_version": "analytics-run-1", "run_id": run_id, **configuration,
            "origin": snapshot.origin, "input_kind": "legacy_analysis_snapshot_not_original_api_response",
            "source_snapshot_id": snapshot.data.get("snapshotId"), "source_created_at": snapshot.data.get("createdAt"),
            "protocol": {k: snapshot.data.get("protocol", {}).get(k) for k in ("id", "code", "version", "cutoff_date", "maxRecordsPerSource")},
            "tables": catalogue, "artifacts": hashes, "notice": summary["notice"]}
        (stage / "manifest.json").write_bytes(json_bytes(manifest))
        destination.parent.mkdir(exist_ok=True)
        try: stage.rename(destination)
        except OSError:
            if not destination.exists(): raise
            return verify_run(root, run_id)
        return verify_run(root, run_id)
    finally:
        # Apenas o diretorio temporario criado nesta chamada, dentro da raiz validada.
        if stage.exists() and stage.resolve().parent == root: shutil.rmtree(stage)


def publish(root, run_id):
    verify_run(root, run_id)
    marker = root / "publications" / (run_id + ".json"); marker.parent.mkdir(exist_ok=True)
    publication = {"run_id": run_id, "manifest_hash": digest((run_path(root, run_id) / "manifest.json").read_bytes())}
    try:
        with marker.open("xb") as stream: stream.write(json_bytes(publication))
    except FileExistsError:
        if json.loads(marker.read_bytes()) != publication: raise ValueError("PUBLICATION_MISMATCH")
    return publication


def require_published(root, run_id):
    folder = run_path(root, run_id)
    marker = root / "publications" / (run_id + ".json")
    publication = json.loads(marker.read_bytes())
    if publication["manifest_hash"] != digest((folder / "manifest.json").read_bytes()): raise ValueError("PUBLICATION_MISMATCH")
    return verify_run(root, run_id)


def public_summary(root, run_id):
    manifest = require_published(root, run_id)
    result = json.loads((run_path(root, run_id) / "summary.json").read_bytes())
    result["protocol"] = manifest["protocol"]
    allowed = {"source", "query", "status", "records_seen", "total_returned", "connector_version", "api_version", "executed_at", "finished_at"}
    result["sourceRuns"] = [{k: v for k, v in row.items() if k in allowed} for row in result.get("sourceRuns", [])]
    return result


def query_table(root, run_id, name, *, offset=0, limit=100, context=None, source=None):
    manifest = require_published(root, run_id)
    if name not in PUBLIC_TABLES or name not in manifest["tables"]: raise ValueError("TABLE_NOT_PUBLIC_OR_UNAVAILABLE")
    clauses, values = [], []
    fields = SCHEMAS[name].names
    if context:
        if "context" not in fields: raise ValueError("FILTER_NOT_APPLICABLE")
        clauses.append('"context"=?'); values.append(context)
    if source:
        if "source" in fields: clauses.append('"source"=?'); values.append(source)
        elif "sources_json" in fields: clauses.append("json_contains(sources_json, ?)"); values.append(json.dumps(source))
        else: raise ValueError("FILTER_NOT_APPLICABLE")
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with duckdb.connect(str(run_path(root, run_id) / "analytics.duckdb"), read_only=True) as db:
        total = db.execute(f'SELECT count(*) FROM "{name}"' + where, values).fetchone()[0]
        columns = ",".join('"' + c + '"' for c in fields)
        cursor = db.execute(f'SELECT * FROM "{name}"' + where + f" ORDER BY {columns} LIMIT ? OFFSET ?", values + [limit, offset])
        rows = [dict(zip(fields, row)) for row in cursor.fetchall()]
    return {"run_id": run_id, "table": name, "total": total, "offset": offset, "limit": limit, "rows": rows,
            "unit": "study" if name.startswith(("mart_", "reviewed_")) else "document_or_registry"}
