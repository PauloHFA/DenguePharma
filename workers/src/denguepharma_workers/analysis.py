"""Analise descritiva v2: python -m denguepharma_workers.analysis --input snapshot.json --output resultados"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
import platform
from importlib.metadata import version
import zipfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
import pandas as pd

SCRIPT_VERSION = "descriptive-2.0.0"
DICTIONARY_VERSION = "descriptive-v2.0"
FIELDS = ["substance", "design", "phase", "serotype", "outcome_category"]
STATES = ["PRESENTE", "NAO_INFORMADO", "NAO_APLICAVEL", "NAO_EXTRAIDO", "INCERTO", "NAO_HOUVE_EVENTO", "SEM_REVISAO", "CONFLITO"]
CONTEXTS = ["HUMANO", "DESAFIO_CONTROLADO", "IN_SILICO", "IN_VITRO", "ANIMAL", "NAO_CLASSIFICADO"]
OUTCOMES = ["CLINICO", "VIROLOGICO", "SEGURANCA", "OUTRO"]
NOTICE = "Analise descritiva do corpus filtrado. Zero registros nao comprova ausencia de evidencia na literatura. Rastreabilidade estrutural nao comprova suporte semantico. Nao estima eficacia nem recomenda medicamentos."
MAX_BYTES = 32 * 1024 * 1024


class Artifacts(dict):
    """Limita o resultado durante a geracao, antes de enviar objetos ao storage."""
    def __init__(self):
        super().__init__()
        self.total_bytes = 0

    def __setitem__(self, name, data):
        total = self.total_bytes - len(self.get(name, b"")) + len(data)
        if len(data) > MAX_BYTES or (name != "bundle.zip" and (total > MAX_BYTES or len(self) >= 256)):
            raise ValueError("ANALYSIS_PACKAGE_LIMIT: restrinja os filtros; resultado nao foi truncado")
        if name != "bundle.zip":
            self.total_bytes = total
        super().__setitem__(name, data)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False).encode("utf-8")


def layer(context: str) -> str:
    if context in {"IN_SILICO", "IN_VITRO", "ANIMAL"}:
        return "PRE_CLINICO"
    if context in {"HUMANO", "DESAFIO_CONTROLADO"}:
        return "CLINICO"
    return "NAO_CLASSIFICADO"


def cell(study, field):
    if field in {"context", "purpose"}:
        value = study.get(field)
        return {"status": "PRESENTE", "value": value} if value and value != "NAO_CLASSIFICADO" else {"status": "SEM_REVISAO"}
    value = study.get("fields", {}).get(field, {"status": "SEM_REVISAO"})
    if not isinstance(value, dict) or value.get("status") not in STATES:
        raise ValueError(f"Estado invalido: {field}")
    if value["status"] == "PRESENTE" and (not isinstance(value.get("value"), str) or not value["value"].strip()):
        raise ValueError(f"Valor presente sem conteudo: {field}")
    return value


def category(value):
    return value["value"] if value["status"] == "PRESENTE" else f"[{value['status']}]"


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def csv_bytes(rows, columns):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    # Neutraliza formulas ao abrir CSV em planilhas; dados originais permanecem no JSON.
    for row in rows:
        writer.writerow({key: ("'" + value if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r")) else value)
                         for key, value in row.items()})
    return stream.getvalue().encode("utf-8")


def analyze(content: bytes):
    snapshot = json.loads(content)
    if snapshot.get("schemaVersion") != "2.0" or snapshot.get("dictionaryVersion") != DICTIONARY_VERSION or snapshot.get("fields") != FIELDS:
        raise ValueError("Schema/dicionario de entrada nao suportado")
    studies, seen = [], {}
    for study in snapshot.get("studies", []):
        key = study.get("studyId")
        if not isinstance(key, str) or not key:
            raise ValueError("studyId obrigatorio")
        if study.get("context") not in CONTEXTS:
            raise ValueError("Contexto invalido")
        for field in FIELDS:
            cell(study, field)
        if key in seen:
            if seen[key] != study:
                raise ValueError("studyId duplicado com dados divergentes")
            continue
        seen[key] = study
        studies.append(study)
    studies.sort(key=lambda row: row["studyId"])
    dimensions = ["context", "purpose"] + FIELDS
    dataset, distributions, completeness, gaps, traceability = [], [], [], [], []
    for study in studies:
        row = {"study_id": study["studyId"], "context": study["context"], "layer": layer(study["context"]),
               "reassessment_pending": bool(study.get("reassessmentPending"))}
        for field in dimensions:
            value = cell(study, field)
            row[field] = value.get("value") if value["status"] == "PRESENTE" else None
            row[field + "_status"] = value["status"]
        dataset.append(row)
    contexts = sorted({s["context"] for s in studies})
    context_counts = [{"context": context, "layer": layer(context), "count": sum(s["context"] == context for s in studies),
                       "denominator": len(studies), "proportion": ratio(sum(s["context"] == context for s in studies), len(studies))} for context in contexts]
    for context in contexts:
        subset = [study for study in studies if study["context"] == context]
        for field in dimensions:
            values = [cell(study, field) for study in subset]
            frame = pd.DataFrame([{"category": category(value), "status": value["status"]} for value in values])
            for (label, state), count in frame.groupby(["category", "status"], sort=True, dropna=False).size().items():
                distributions.append({"context": context, "layer": layer(context), "field": field, "category": label, "status": state,
                                      "count": int(count), "denominator": len(subset), "proportion": ratio(int(count), len(subset))})
            if field in FIELDS:
                counts = {state: sum(value["status"] == state for value in values) for state in STATES}
                applicable = len(subset) - counts["NAO_APLICAVEL"]
                completeness.append({"context": context, "field": field, "present": counts["PRESENTE"], "applicable": applicable,
                                     "total": len(subset), "proportion": ratio(counts["PRESENTE"], applicable), "states": counts})
    # Categorias globais do corpus + categorias vazias previstas; cada contexto permanece um estrato separado.
    substances = sorted({category(cell(study, "substance")) for study in studies})
    outcome_categories = sorted(set(OUTCOMES) | {category(cell(study, "outcome_category")) for study in studies})
    for context in CONTEXTS if studies else []:
        subset = [study for study in studies if study["context"] == context]
        denominator = len(subset)
        substance_column = pd.Series(pd.Categorical([category(cell(s, "substance")) for s in subset], categories=substances))
        outcome_column = pd.Series(pd.Categorical([category(cell(s, "outcome_category")) for s in subset], categories=outcome_categories))
        matrix = pd.crosstab(substance_column, outcome_column, dropna=False).reindex(index=substances, columns=outcome_categories, fill_value=0)
        for substance in substances:
            count = sum(category(cell(s, "substance")) == substance for s in subset)
            gaps.append({"map": "substance_context", "layer": layer(context), "context": context, "substance": substance,
                         "category": context, "count": count, "denominator": denominator})
            for outcome in outcome_categories:
                gaps.append({"map": "substance_outcome", "layer": layer(context), "context": context, "substance": substance,
                             "category": outcome, "count": int(matrix.at[substance, outcome]), "denominator": denominator})
    references = {}
    for study in studies:
        for ref in study.get("references", []):
            if ref.get("field") not in FIELDS or not ref.get("fieldId"):
                raise ValueError("Referencia analitica invalida")
            references.setdefault(ref["fieldId"], ref)
    refs = list(references.values())
    present_refs = [ref for ref in refs if ref.get("absenceStatus") == "PRESENTE"]
    for name, subset, predicate in [
        ("identifiers", refs, lambda r: bool(r.get("hasIdentifier"))),
        ("versions", refs, lambda r: bool(r.get("hasVersion"))),
        ("locators", present_refs, lambda r: bool(r.get("hasLocator"))),
        ("complete_structure", present_refs, lambda r: all(r.get(k) for k in ("hasIdentifier", "hasVersion", "hasLocator"))),
    ]:
        numerator = sum(predicate(ref) for ref in subset)
        traceability.append({"metric": name, "numerator": numerator, "denominator": len(subset), "proportion": ratio(numerator, len(subset))})
    summary = {"schemaVersion": "2.0", "scriptVersion": SCRIPT_VERSION, "dictionaryVersion": DICTIONARY_VERSION,
               "status": "COMPLETE" if studies else "NO_DATA", "notice": NOTICE,
               "studyCount": len(studies), "documentCount": len({ref["documentId"] for ref in refs if ref.get("documentId")}),
               "reassessmentPendingCount": sum(bool(study.get("reassessmentPending")) for study in studies),
               "contextCounts": context_counts, "distributions": distributions, "completeness": completeness,
               "gaps": gaps, "traceability": traceability}
    return summary, dataset


def chart(rows, title, value_key, label_key):
    # Figuras completas: dividir em blocos, sem descartar categorias fora de um top-N.
    figure = Figure(figsize=(9, max(3, len(rows) * 0.32)))
    axis = figure.subplots()
    axis.barh(range(len(rows)), [r[value_key] for r in rows], color="#176b87")
    axis.set_yticks(range(len(rows)), [str(r[label_key])[:140] for r in rows])
    axis.invert_yaxis()
    axis.set_title(title)
    axis.set_xlabel("Numero de estudos no contexto")
    axis.xaxis.get_major_locator().set_params(integer=True)
    figure.tight_layout()
    stream = io.BytesIO()
    figure.savefig(stream, format="png", dpi=110, metadata={"Software": SCRIPT_VERSION})
    figure.clear()
    return stream.getvalue()


def gap_chart(rows, title, columns):
    substances = sorted({row["substance"] for row in rows})
    figure = Figure(figsize=(max(8, len(columns) * 1.2), max(3, len(substances) * 0.36)))
    axis = figure.subplots()
    matrix = [[next((row["count"] for row in rows if row["substance"] == substance and row["category"] == col), 0) for col in columns] for substance in substances]
    image = axis.imshow(matrix, aspect="auto", cmap="Blues", vmin=0, vmax=max(1,max(max(row) for row in matrix)))
    axis.set_yticks(range(len(substances)), [s[:140] for s in substances])
    axis.set_xticks(range(len(columns)), columns, rotation=35, ha="right")
    axis.set_title(title)
    colorbar=figure.colorbar(image, ax=axis, label="Estudos no corpus filtrado")
    colorbar.locator=MaxNLocator(integer=True,nbins=6)
    colorbar.update_ticks()
    figure.tight_layout()
    stream=io.BytesIO(); figure.savefig(stream, format="png", dpi=110, metadata={"Software": SCRIPT_VERSION}); figure.clear()
    return stream.getvalue()


def bundle(content: bytes) -> dict[str, bytes]:
    if json.loads(content).get("schemaVersion") == "3.0":
        from .corpus import bundle as corpus_bundle
        return corpus_bundle(content)
    summary, dataset = analyze(content)
    files = Artifacts()
    files["dataset.json"] = content
    files["summary.json"] = json_bytes(summary)
    dimensions = ["context", "purpose"] + FIELDS
    columns = ["study_id", "layer", "reassessment_pending"] + [col for field in dimensions for col in (field, field + "_status")]
    files["dataset.csv"] = csv_bytes(dataset, columns)
    files["distributions.csv"] = csv_bytes(summary["distributions"], ["layer", "context", "field", "category", "status", "count", "denominator", "proportion"])
    completeness = [{**row, "states": json.dumps(row["states"], sort_keys=True)} for row in summary["completeness"]]
    files["completeness.csv"] = csv_bytes(completeness, ["context", "field", "present", "applicable", "total", "proportion", "states"])
    files["gaps.csv"] = csv_bytes(summary["gaps"], ["map", "layer", "context", "substance", "category", "count", "denominator"])
    files["traceability.csv"] = csv_bytes(summary["traceability"], ["metric", "numerator", "denominator", "proportion"])
    figures = []
    for context in sorted({row["context"] for row in summary["distributions"]}):
        for field in ["purpose"] + FIELDS:
            rows = [row for row in summary["distributions"] if row["context"] == context and row["field"] == field]
            for page, start in enumerate(range(0, len(rows), 30)):
                name = f"figures/{context.lower()}_{field}_{page + 1}.png"
                files[name] = chart(rows[start:start + 30], f"{context} — {field}", "count", "category")
                figures.append(name)
        gap_rows = [row for row in summary["gaps"] if row["context"] == context and row["map"] == "substance_outcome"]
        substances = sorted({row["substance"] for row in gap_rows})
        for page, start in enumerate(range(0, len(substances), 30)):
            selected=set(substances[start:start+30])
            rows=[row for row in gap_rows if row["substance"] in selected]
            name=f"figures/{context.lower()}_gaps_{page+1}.png"
            files[name]=gap_chart(rows,f"{context} — substancia x desfecho",sorted({row["category"] for row in rows}))
            figures.append(name)
    for group in sorted({row["layer"] for row in summary["gaps"]}):
        gap_rows=[row for row in summary["gaps"] if row["layer"] == group and row["map"] == "substance_context"]
        substances=sorted({row["substance"] for row in gap_rows})
        for page,start in enumerate(range(0,len(substances),30)):
            selected=set(substances[start:start+30]); rows=[row for row in gap_rows if row["substance"] in selected]
            name=f"figures/{group.lower()}_contexts_{page+1}.png"
            files[name]=gap_chart(rows,f"{group} — inventario por contexto", sorted({row["category"] for row in rows}))
            figures.append(name)
    # HTML escapa todos os valores curados e nao carrega recursos externos.
    rows_html = "".join(f"<tr><td>{html.escape(row['context'])}</td><td>{html.escape(row['field'])}</td><td>{html.escape(str(row['category']))}</td><td>{row['count']}</td><td>{row['denominator']}</td></tr>" for row in summary["distributions"])
    images = "".join(f'<figure><img alt="Distribuicao descritiva" style="max-width:100%" src="{name}"><figcaption>{name}</figcaption></figure>' for name in figures)
    quality = "".join(f"<h2>{title}</h2>" + pd.DataFrame(summary[key]).to_html(index=False, escape=True, na_rep="Sem dados")
                      for key,title in [("completeness","Completude e estados"),("traceability","Rastreabilidade estrutural"),("gaps","Lacunas do corpus")])
    files["report.html"] = (f'<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>Analise descritiva</title>'
                            f'<h1>Analise descritiva de evidencias revisadas</h1><p>{NOTICE}</p><p>Estudos: {summary["studyCount"]}. '
                            f'Documentos referenciados: {summary["documentCount"]}.</p>'
                            + ('<p>Sem dados para os filtros selecionados.</p>' if summary["status"] == "NO_DATA" else '')
                            + f'<table><thead><tr><th>Contexto</th><th>Campo</th><th>Categoria</th><th>Contagem</th><th>Denominador</th></tr></thead><tbody>{rows_html}</tbody></table>{quality}{images}</html>').encode("utf-8")
    manifest = {"schemaVersion": "2.0", "scriptVersion": SCRIPT_VERSION, "dictionaryVersion": DICTIONARY_VERSION,
                "inputHash": digest(content), "configuration": {"unit": "study", "stratifyBy": "context", "dropna": False},
                "scriptHash": digest(Path(__file__).read_bytes()),
                "dependencies": {"python": platform.python_version(), "pandas": pd.__version__, "matplotlib": matplotlib.__version__,
                                 "numpy": version("numpy"), "pillow": version("pillow")},
                "artifacts": {name: digest(data) for name, data in sorted(files.items())}}
    files["manifest.json"] = json_bytes(manifest)
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            entry = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, data)
    files["bundle.zip"] = stream.getvalue()
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    content = Path(args.input).read_bytes()
    files = bundle(content)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    print(f"Analise concluida: {output / 'bundle.zip'}")


if __name__ == "__main__":
    main()
