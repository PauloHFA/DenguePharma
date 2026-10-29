from __future__ import annotations

import html
from importlib.resources import files
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import duckdb

from ..domain import digest, json_bytes
from ..storage import run_path, verify_run


def render(root: Path, run_id: str, quarto: str | None = None):
    root = root.resolve(); manifest = verify_run(root, run_id)
    executable = quarto or os.getenv("QUARTO_BIN") or shutil.which("quarto")
    if not executable: raise ValueError("QUARTO_NOT_INSTALLED: configure QUARTO_BIN")
    destination = root / "reports" / run_id
    if destination.exists():
        existing = json.loads((destination / "manifest.json").read_bytes())
        if digest((destination / "report.html").read_bytes()) != existing["html_hash"]: raise ValueError("REPORT_HASH_MISMATCH")
        return existing
    stage = Path(tempfile.mkdtemp(prefix="quarto-", dir=root))
    try:
        summary = json.loads((run_path(root, run_id) / "summary.json").read_bytes())
        template = files("denguepharma_analytics.reports").joinpath("report.qmd").read_text(encoding="utf-8")
        cutoff = str(manifest["protocol"].get("cutoff_date") or "Sem corte informado")
        # YAML usa string JSON; metadados externos nunca viram codigo executavel.
        template = template.replace('"{{CUTOFF}}"', json.dumps(cutoff))
        with duckdb.connect(str(run_path(root, run_id) / "analytics.duckdb"), read_only=True) as db:
            def table(name, title):
                frame = db.execute(f'SELECT * FROM "{name}"').fetchdf()
                content = frame.to_html(index=False, escape=True, na_rep="Sem dados") if len(frame) else "<p>Sem dados nesta camada.</p>"
                return "<h3>"+html.escape(title)+"</h3>"+content
            blocks = {
                "PROVENANCE": "<p>Execução: <code>"+run_id+"</code><br>Hash de entrada: <code>"+manifest["input_hash"]+"</code><br>Corte: "+html.escape(cutoff)+"</p>",
                "OVERVIEW": f'<p>Documentos: <strong>{summary["documentCount"]}</strong>; publicações: <strong>{summary["publicationCount"]}</strong>; registros de ensaios: <strong>{summary["trialCount"]}</strong>; estudos revisados: <strong>{summary["studyCount"]}</strong>.</p>',
                "TEMPORAL": table("corpus_temporal", "Distribuição temporal: contagem, denominador e unidade"),
                "TEMPORAL_FLAGS": table("corpus_temporal_flags", "Datas para conferência"),
                "DISTRIBUTIONS": table("corpus_distributions", "Categorias dos registros coletados"),
                "COMPLETENESS": table("corpus_completeness", "Disponibilidade: valores presentes / registros aplicáveis"),
                "ENROLLMENT": table("corpus_enrollment", "Participantes informados por registro"),
                "REVIEWED_NOTICE": "<p>"+html.escape(summary["reviewed"]["notice"])+"</p>",
                "PANORAMA": table("mart_panorama", "Panorama por estudo revisado"),
                "REVIEWED_COMPLETENESS": table("reviewed_completeness", "Completude dos campos revisados"),
                "WARNINGS": "<ul>"+"".join("<li>"+html.escape(w)+"</li>" for w in summary["warnings"])+"</ul>",
            }
            for key, value in blocks.items(): template = template.replace("{{"+key+"}}", value)
            clinical="<p>Sem resultados clínicos revisados. A revisão humana permanece pendente; isto não significa ausência de benefício ou evidência inconclusiva.</p>"
            if "clinical_results" in manifest["tables"]:
                clinical+=table("clinical_screening","Seleção independente — estado por estudo")+table("clinical_results","Resultados por estudo, braço, população, desfecho e tempo")+table("clinical_synthesis","Julgamentos humanos e justificativas")+table("clinical_references","Referências e localizadores")+table("clinical_absences","Ausências de estudo confirmadas no corpus")
                if manifest["tables"]["clinical_results"]["rows"]: clinical=clinical.replace("<p>Sem resultados clínicos revisados. A revisão humana permanece pendente; isto não significa ausência de benefício ou evidência inconclusiva.</p>","")
            import base64
            publications="<p>Auditoria de referências indisponível nesta execução.</p>"
            if "publication_reference_links" in manifest["tables"]:
                publications="<p>"+html.escape(summary["publication_references"]["notice"])+"</p>"+table("publication_reference_coverage","Cobertura por tipo de referência")+table("publication_reference_missing","PMIDs não recuperados no corpus")+table("publication_reference_links","Candidatos bibliográficos e proveniência")
            reporting="<p>Auditoria de datas indisponível nesta execução.</p>"
            if "reporting_registry" in manifest["tables"]:
                reporting="<p>"+html.escape(summary["reporting"]["notice"])+"</p>"+table("reporting_results_by_status","Disponibilidade declarada por status")+table("reporting_intervals","Intervalos de calendário entre pares válidos")+table("reporting_registry","Datas, flags e proveniência")
            sponsors="<p>Metadados de patrocinador não analisados nesta execução.</p>"
            if "corpus_sponsor_trials" in manifest["tables"]:
                sponsors="<p>"+html.escape(summary["sponsors"]["notice"])+"</p>"+table("corpus_sponsor_distributions","Patrocinadores declarados — contagens e denominadores")+table("corpus_sponsor_completeness","Disponibilidade neste snapshot")+table("corpus_sponsor_trials","Registros e referências documentais")
            calibration="<p>Diagnóstico de calibração indisponível nesta versão.</p>"
            if "calibration_signals" in manifest["tables"]:
                calibration="<p>"+html.escape(summary["calibration"]["notice"])+"</p>"+table("calibration_signals","Sinais de metadados — não são decisões de exclusão")+table("calibration_intervention_types","Tipos de intervenção declarados pelos registros")+table("calibration_searches","Recuperação no piloto e totais informados pelas buscas")
            for name in sorted(manifest["artifacts"]):
                if name.startswith("figures/") and name.endswith(".png"):
                    content=base64.b64encode((run_path(root,run_id)/name).read_bytes()).decode()
                    figure='<img style="max-width:100%" alt="'+("Cobertura bibliográfica por PMID, sem confirmação clínica" if name.startswith("figures/publication-refs-") else "Auditoria de datas: mediana e intervalo interquartil" if name.startswith("figures/reporting-") else "Patrocinadores declarados nos registros" if name.startswith("figures/sponsors-") else "Sinais de metadados para revisão" if name.startswith("figures/calibration-") else "Efeitos individuais, sem estimativa combinada")+'" src="data:image/png;base64,'+content+'">'
                    if name.startswith("figures/publication-refs-"): publications+=figure
                    elif name.startswith("figures/reporting-"): reporting+=figure
                    elif name.startswith("figures/sponsors-"): sponsors+=figure
                    elif name.startswith("figures/calibration-"): calibration+=figure
                    else: clinical+=figure
            template=template.replace("{{CLINICAL}}",clinical)
            template=template.replace("{{CALIBRATION}}",calibration)
            template=template.replace("{{SPONSORS}}",sponsors)
            template=template.replace("{{REPORTING}}",reporting)
            template=template.replace("{{PUBLICATION_REFS}}",publications)
        (stage / "report.qmd").write_text(template, encoding="utf-8", newline="\n")
        completed = subprocess.run([executable, "render", "report.qmd", "--to", "html", "--output", "report.html"], cwd=stage,
                                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
        if completed.returncode: raise RuntimeError("QUARTO_RENDER_FAILED: " + completed.stderr[-1500:])
        report = {"run_id": run_id, "input_hash": manifest["input_hash"], "manifest_hash": digest((run_path(root, run_id)/"manifest.json").read_bytes()),
            "html_hash": digest((stage / "report.html").read_bytes()), "template_hash": digest((stage / "report.qmd").read_bytes()),
            "quarto_version": subprocess.check_output([executable, "--version"], text=True, timeout=10).strip()}
        (stage / "manifest.json").write_bytes(json_bytes(report))
        destination.parent.mkdir(exist_ok=True); stage.rename(destination)
        return report
    finally:
        if stage.exists() and stage.resolve().parent == root: shutil.rmtree(stage)
