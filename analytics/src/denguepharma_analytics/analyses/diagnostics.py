"""Diagnostico do corpus coletado, distinto do panorama cientifico por estudo."""
from __future__ import annotations
from collections import Counter
import json
import pandas as pd
from ..domain import FIELDS, MISSING, CORPUS_NOTICE as NOTICE, json_bytes, ratio
from ..identity.identifiers import year, text
from ..preparation.documents import prepare
from .reviewed import analyze as reviewed_analysis

def frequencies(records, field, unit, multi=False, population=None):
    """Categorias ausentes explicitas. Multivalor conta cada unidade uma vez por categoria."""
    counts = Counter()
    for record in records:
        value = record.get(field)
        categories = set(value or [MISSING]) if multi else {value if value is not None else MISSING}
        counts.update(categories)
    return [{"field": field, "category": str(category), "count": count, "denominator": len(records),
             "proportion": ratio(count, len(records)), "unit": unit, "overlapping": multi, "population": population or "corpus_coletado"}
            for category, count in sorted(counts.items(), key=lambda item: str(item[0]))]


def analyze(content):
    snapshot = json.loads(content)
    records, conflicts, audit = prepare(snapshot)
    publications = [r for r in records if r["document_type"] == "PUBLICACAO"]
    trials = [r for r in records if r["document_type"] == "REGISTRO_ENSAIO"]
    cutoff_year = year(snapshot.get("protocol", {}).get("cutoff_date"))
    temporal_flags = [{"document_id": r["document_id"], "publication_year": r["publication_year"], "status": "ANO_BIBLIOGRAFICO_APOS_CORTE_CONFERIR_FONTE"}
                      for r in publications if cutoff_year and r["publication_year"] and r["publication_year"] > cutoff_year]
    distributions = []
    for subset, field, multi, unit in [(records, "sources", True, "documento"), (records, "context", False, "documento"),
                                      (records, "screening_states", True, "documento"),
                                      (publications, "publication_types", True, "publicacao"),
                                      (trials, "design", False, "registro_ensaio"), (trials, "phases", True, "registro_ensaio"),
                                      (trials, "recruitment", False, "registro_ensaio"), (trials, "substances", True, "registro_ensaio"),
                                      (trials, "countries", True, "registro_ensaio"), (trials, "has_results", False, "registro_ensaio")]:
        distributions.extend(frequencies(subset, field, unit, multi))
    temporal = frequencies(publications, "publication_year", "publicacao") + frequencies(trials, "start_year", "registro_ensaio")
    completeness = []
    for subset, unit, fields in [(publications, "publicacao", ["publication_year", "journal", "language", "identifiers"]),
                                 (trials, "registro_ensaio", ["start_year", "design", "phases", "recruitment", "countries", "substances", "has_results", "enrollment"])]:
        for source in sorted({s for r in subset for s in r["sources"]}):
            selected = [r for r in subset if source in r["sources"]]
            for field in fields:
                counts = Counter()
                for r in selected:
                    if field in r["conflict_fields"] or (field == "enrollment" and any(f.startswith("enrollment_") for f in r["conflict_fields"])):
                        counts["CONFLITO"] += 1
                    elif field == "phases" and (r.get("phases") == ["NA"] or (r.get("design") == "OBSERVATIONAL" and not r.get("phases"))):
                        counts["NAO_APLICAVEL"] += 1
                    elif field == "enrollment":
                        counts["PRESENTE" if any(r[f] is not None for f in ("enrollment_estimated", "enrollment_actual", "enrollment_unknown_type")) else "NAO_INFORMADO"] += 1
                    else:
                        value = r.get(field)
                        counts["PRESENTE" if value is not None and value != [] and value != "" else "NAO_INFORMADO"] += 1
                completeness.append({"source": source, "field": field, "unit": unit, "review_status": "METADADO_DA_FONTE",
                                     "present": counts["PRESENTE"], "applicable": len(selected)-counts["NAO_APLICAVEL"], "total": len(selected), "conflicts": counts["CONFLITO"],
                                     "not_applicable": counts["NAO_APLICAVEL"], "missing": counts["NAO_INFORMADO"],
                                     "proportion": ratio(counts["PRESENTE"], len(selected)-counts["NAO_APLICAVEL"])})
    # Referencias bibliograficas geram candidatos; apenas vinculos curatoriais confirmam estudos.
    links, candidates = [], []
    for trial in trials:
        matched = [p for p in publications if trial["study_id"] and p["study_id"] == trial["study_id"]]
        for p in matched:
            links.append({"trial_document_id": trial["document_id"], "publication_document_id": p["document_id"], "study_id": trial["study_id"], "status": "CONFIRMADO"})
        for pmid in trial["referenced_pmids"]:
            for p in publications:
                if pmid in p["identifiers"] and p not in matched:
                    candidates.append({"trial_document_id": trial["document_id"], "publication_document_id": p["document_id"], "identifier": pmid, "status": "CANDIDATO_REVISAO"})
    enrollment = []
    for field in ("enrollment_estimated", "enrollment_actual", "enrollment_unknown_type"):
        values = [r[field] for r in trials if r[field] is not None]
        series = pd.Series(values, dtype="float64")
        enrollment.append({"field": field, "available": len(values), "denominator": len(trials), "missing": len(trials)-len(values),
                           "median": float(series.median()) if values else None,
                           "q1": float(series.quantile(.25)) if values else None,
                           "q3": float(series.quantile(.75)) if values else None,
                           "min": min(values) if values else None, "max": max(values) if values else None,
                           "unit": "registro_ensaio", "sumsParticipants": False})
    previous = snapshot.get("previous")
    changes = {"status": "NO_BASELINE", "new": [], "changed": [], "notObserved": [], "comparable": None}
    if previous:
        old = {d["documentId"]: d.get("contentHash") for d in previous.get("documents", [])}
        now = {d["documentId"]: d.get("contentHash") for d in snapshot.get("documents", [])}
        old_protocol, current = previous.get("protocol", {}), snapshot.get("protocol", {})
        changes = {"status": "COMPARED", "baselineAnalysisId": previous.get("analysisId"),
                   "comparable": old_protocol.get("id") == current.get("id"),
                   "new": sorted(now.keys()-old.keys()), "changed": sorted(k for k in now.keys() & old.keys() if now[k] != old[k]),
                   "notObserved": sorted(old.keys()-now.keys()),
                   "notice": "Nao observado nao significa retratacao. Protocolos diferentes podem alterar a cobertura."}
    reviewed = {"schemaVersion": "2.0", "dictionaryVersion": "descriptive-v2.0", "fields": FIELDS,
                "studies": snapshot.get("studies", [])}
    evidence, _ = reviewed_analysis(json_bytes(reviewed))
    scientific_fields = snapshot.get("scientificFields", [])
    scientific_availability = []
    for context in sorted({s["context"] for s in snapshot.get("studies", [])}):
        study_ids = {s["studyId"] for s in snapshot["studies"] if s["context"] == context}
        for field in ("population", "comparator", "limitations", "outcome_definition", "sample_size"):
            states = Counter()
            for study_id in study_ids:
                annotations = [r for r in scientific_fields if r.get("study_id") == study_id and r.get("field_name") == field]
                distinct = {(r.get("status"), r.get("value") if r.get("status") == "PRESENTE" else None) for r in annotations}
                state = "SEM_REVISAO" if not distinct else "CONFLITO" if len(distinct) > 1 else next(iter(distinct))[0]
                if state == "PRESENTE" and not text(next(iter(distinct))[1]): state = "INCERTO"
                states[state] += 1
            applicable = len(study_ids)-states["NAO_APLICAVEL"]
            scientific_availability.append({"context": context, "field": field, "present": states["PRESENTE"], "applicable": applicable,
                                            "total": len(study_ids), "proportion": ratio(states["PRESENTE"], applicable), "states": dict(states)})
    linked = len({link["trial_document_id"] for link in links})
    summary = {"schemaVersion": "3.0", "dictionaryVersion": "corpus-v3.0", "status": "COMPLETED" if records else "NO_DATA",
               "notice": NOTICE, "protocol": snapshot.get("protocol"), "sourceRuns": snapshot.get("sourceRuns", []),
               "documentCount": len(records), "rawDocumentCount": len(snapshot.get("documents", [])),
               "publicationCount": len(publications), "trialCount": len(trials), "studyCount": evidence["studyCount"],
               "distinctConfirmedStudyCount": len({r["study_id"] for r in records if r["study_id"]}),
               "temporal": temporal, "temporalFlags": temporal_flags, "distributions": distributions, "completeness": completeness,
               "enrollment": enrollment, "conflicts": conflicts, "transformations": audit,
               "links": links, "linkCandidates": candidates,
               "linkCoverage": {"numerator": linked, "denominator": len(trials), "proportion": ratio(linked, len(trials)), "unit": "registro_ensaio"},
               "changes": changes, "reviewed": evidence, "scientificFieldAvailability": scientific_availability,
               "warnings": ["Nomes recebem normalizacao lexical ou vinculo exato e nao ambiguo ao cadastro PubChem; isso nao confirma eficacia nem aprovacao regulatoria.",
                            "Percentuais de paises e intervencoes podem somar mais de 100%.",
                            "Metadados coletados podem conter registros inelegiveis, inclusive vacinas pendentes de exclusao.",
                            "Ano bibliografico e data usada na busca podem divergir; anos posteriores ao corte sao preservados e sinalizados para conferencia.",
                            "Coleta nao e uma reconstrucao historica completa das bases."]}
    return summary, records
