"""Agregacoes de campos revisados; a unidade e study_id."""
from __future__ import annotations
import json
import pandas as pd
from ..domain import FIELDS, STATES, CONTEXTS, OUTCOMES, DICTIONARY_VERSION, SCRIPT_VERSION, NOTICE, ratio, layer

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
