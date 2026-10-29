"""Resultados publicos versionados e curadoria clinica protegida."""
from __future__ import annotations

import csv
from io import StringIO
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response

from . import __version__
from .domain import digest
from .marts import PUBLIC_TABLES
from .storage import default_root, public_summary, query_table, require_published, run_path

CAPABILITIES = {
    "architecture": "FastAPI + Streamlit + Quarto", "version": __version__, "mode": "public_analytics_protected_clinical_curation",
    "curation": {"state": "clinical_protected_legacy_auth", "new_api_writes": True},
    "clinical": {"state":"implemented_pending_human_review","pooling":False,"ranking":False,"automatic_conclusions":False},
    "axes": {
        "A": {"state": "parcial", "available": ["corpus_diagnostics", "reviewed_descriptive", "collected_trial_sponsors"], "pending": ["reviewed_study_sponsors", "confidence_intervals", "temporal_regression"]},
        "B": {"state": "parcial", "description": "Auditorias de datas e referencias; censura, Kaplan-Meier, vinculos conferidos e discrepancias ainda pendentes", "available":["registry_date_audit","observed_calendar_intervals","publication_reference_coverage"],"pending":["censoring","kaplan_meier","verified_publication_links","associated_models","discrepancies"]},
        "C": {"state": "planejado", "description": "Pesquisa e carga de doenca"},
        "D": {"state": "planejado", "description": "Avaliacao manual/regras/IA com referencia adjudicada"},
        "E": {"state": "opcional_planejado", "description": "Grafo de evidencias aprovadas"},
    },
}


def public_manifest(manifest):
    return {k: manifest[k] for k in ("schema_version", "run_id", "version", "dictionary", "input_hash", "code_hash", "dependencies", "protocol", "notice")} | {
        "tables": {name: {**info, "file_hash": manifest["artifacts"][info["file"]]} for name, info in manifest["tables"].items() if name in PUBLIC_TABLES},
        "figures":{name:hash_ for name,hash_ in manifest["artifacts"].items() if name.startswith("figures/") and name.endswith(".png")}}


def csv_content(rows, columns):
    stream = StringIO(newline=""); writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n"); writer.writeheader()
    for row in rows:
        writer.writerow({k: "'"+v if isinstance(v, str) and v.startswith(("=", "+", "-", "@", "\t", "\r")) else v for k, v in row.items()})
    return stream.getvalue().encode("utf-8")


def create_app(data_root: Path | None = None, *, authenticate=None):
    root = (data_root or default_root()).resolve()
    app = FastAPI(title="DenguePharma Analytics", version=__version__, description="Resultados publicos; curadoria clinica privada com revisao independente.")
    from .clinical.router import router
    app.include_router(router(root,authenticate))
    from fastapi import Request
    from fastapi.responses import JSONResponse
    @app.exception_handler(PermissionError)
    async def forbidden(request: Request, error: PermissionError): return JSONResponse(status_code=403,content={"detail":"Permissao insuficiente ou revisao sem independencia"})

    @app.get("/health")
    def health(): return {"status": "UP", "mode": "public_read_protected_curation"}

    @app.get("/api/capabilities")
    def capabilities(): return CAPABILITIES

    def comparison_result(baseline,current):
        from .comparison import compare
        try:return compare(root,baseline,current)
        except FileNotFoundError:raise HTTPException(404,"Execucao nao publicada") from None
        except ValueError as error:raise HTTPException(409,str(error)) from None

    @app.get("/api/public/comparisons")
    def comparison(baseline: str,current: str):return comparison_result(baseline,current)

    @app.get("/api/public/comparisons/artifacts")
    def comparison_artifact(baseline: str,current: str,name: str):
        from .comparison import artifacts
        if name not in {"comparison.json","document_changes.csv","table_changes.csv","manifest.json"}:raise HTTPException(404,"Artefato de comparacao inexistente")
        files=artifacts(comparison_result(baseline,current))
        return Response(files[name],media_type="text/csv;charset=utf-8" if name.endswith(".csv") else "application/json",headers={"Content-Disposition":f'attachment; filename="{name}"'})

    def check(run_id):
        try: return require_published(root, run_id)
        except FileNotFoundError: raise HTTPException(404, "Execucao nao publicada") from None
        except (ValueError, KeyError, json.JSONDecodeError): raise HTTPException(409, "Integridade da execucao invalida") from None

    @app.get("/api/public/analyses")
    def analyses():
        markers = sorted((root / "publications").glob("*.json"), key=lambda p: p.stat().st_mtime_ns, reverse=True)
        result = []
        for marker in markers[:200]:
            run_id = marker.stem; manifest = check(run_id); summary = public_summary(root, run_id)
            result.append({"id": run_id, "input_hash": manifest["input_hash"], "protocol": manifest["protocol"],
                "document_count": summary["documentCount"], "publication_count": summary["publicationCount"],
                "trial_count": summary["trialCount"], "reviewed_study_count": summary["studyCount"]})
        return result

    @app.get("/api/public/analyses/{run_id}")
    def analysis(run_id: str): return public_manifest(check(run_id))

    @app.get("/api/public/analyses/{run_id}/summary")
    def summary(run_id: str):
        check(run_id); return public_summary(root, run_id)

    @app.get("/api/public/analyses/{run_id}/tables/{table}")
    def table(run_id: str, table: str, offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000), context: str | None = None, source: str | None = None):
        manifest=check(run_id)
        if table not in PUBLIC_TABLES or table not in manifest["tables"]: raise HTTPException(404, "Tabela nao publica ou indisponivel nesta versao")
        try: return query_table(root, run_id, table, offset=offset, limit=limit, context=context, source=source)
        except ValueError: raise HTTPException(422, "Filtro nao aplicavel a esta tabela") from None

    @app.get("/api/public/analyses/{run_id}/artifacts")
    def artifact(run_id: str, name: str):
        manifest = check(run_id)
        if name == "manifest.json": return public_manifest(manifest)
        if name == "summary.json": return public_summary(root, run_id)
        if name=="research_findings.md" and name in manifest["artifacts"]:
            return FileResponse(run_path(root,run_id)/name,media_type="text/markdown;charset=utf-8",filename=name)
        if name.startswith("figures/") and name.endswith(".png") and name in manifest["artifacts"]:
            return FileResponse(run_path(root,run_id)/name,media_type="image/png",filename=Path(name).name)
        for table_name in sorted(PUBLIC_TABLES.intersection(manifest["tables"])):
            info = manifest["tables"][table_name]
            if name == info["file"]:
                return FileResponse(run_path(root, run_id) / info["file"], media_type="application/vnd.apache.parquet", filename=table_name+".parquet")
            if name == table_name + ".csv":
                total = query_table(root, run_id, table_name, limit=1)["total"]
                rows = []
                for offset in range(0, total, 1000): rows.extend(query_table(root, run_id, table_name, offset=offset, limit=1000)["rows"])
                return Response(csv_content(rows, [f["name"] for f in info["schema"]]), media_type="text/csv;charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{table_name}.csv"'})
        if name == "report.html":
            folder = root / "reports" / run_id
            try:
                report = json.loads((folder / "manifest.json").read_bytes())
                content = (folder / "report.html").read_bytes()
                if report["run_id"] != run_id or report["html_hash"] != digest(content): raise ValueError("REPORT_HASH")
                return Response(content, media_type="text/html", headers={"Content-Disposition": 'attachment; filename="report.html"', "X-Content-Type-Options": "nosniff"})
            except FileNotFoundError: raise HTTPException(404, "Relatorio Quarto ainda nao gerado") from None
            except (ValueError, KeyError): raise HTTPException(409, "Integridade do relatorio invalida") from None
        raise HTTPException(404, "Artefato nao publico")

    return app


app = create_app()
