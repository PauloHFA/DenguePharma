"""Preparacao e analise do corpus v3. Nao infere classificacoes ou eficacia."""
from __future__ import annotations

from collections import Counter, defaultdict
import base64
import hashlib
import html
import io
import json
from pathlib import Path
import platform
import re
import zipfile
from importlib.metadata import version

import matplotlib
from matplotlib.figure import Figure
from matplotlib.patches import Polygon
import pandas as pd

from .analysis import Artifacts, FIELDS, analyze as reviewed_analysis, bundle as reviewed_bundle, csv_bytes, digest, json_bytes, ratio

SCRIPT_VERSION = "corpus-3.0.2"
NOTICE = ("Panorama descritivo de registros coletados: a elegibilidade pode estar pendente. "
          "Evidencias revisadas sao apresentadas separadamente. Frequencia nao mede eficacia; "
          "completude nao mede risco de vies. Zero registros nao demonstra ausencia na literatura.")
MISSING = "[NAO_INFORMADO]"
COUNTRY_ALIASES = {"United States": "United States of America", "South Korea": "South Korea", "Republic of Korea": "South Korea",
                   "Russian Federation": "Russia", "Viet Nam": "Vietnam", "Türkiye": "Turkey", "Czechia": "Czech Republic"}


def text(value):
    return value.strip() if isinstance(value, str) and value.strip() else None


def year(value):
    if not isinstance(value, str):
        return None
    match = re.match(r"^(\d{4})(?:\D|$)", value)
    return int(match[1]) if match and 1800 <= int(match[1]) <= 2200 else None


def identifier(kind, value):
    value = text(value)
    if not value:
        return None
    if kind == "DOI":
        value = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", value, flags=re.I).lower()
    else:
        value = value.upper()
    return f"{kind}:{value}"


def document_identifiers(document):
    metadata = document.get("metadata", {})
    ids = [identifier(k, metadata.get(n)) for k, n in (("PMID", "pmid"), ("DOI", "doi"), ("PMCID", "pmcid"))]
    nct = metadata.get("protocolSection", {}).get("identificationModule", {}).get("nctId")
    if nct:
        ids.append(identifier("NCT", nct))
    return sorted(set(i for i in ids if i))


def prepare(snapshot):
    """Deduplica documentos por identificador exato; ambiguidades nunca fundem estudos."""
    if snapshot.get("schemaVersion") != "3.0" or snapshot.get("dictionaryVersion") != "corpus-v3.0":
        raise ValueError("CORPUS_SCHEMA_INVALID")
    documents = snapshot.get("documents", [])
    chemical_index = defaultdict(dict)
    for mapping in snapshot.get("chemicalMappings", []):
        cid = mapping.get("pubchem_cid")
        if not cid:
            continue
        for name in (mapping.get("published_name"), mapping.get("normalized_name"), mapping.get("alias")):
            if text(name):
                chemical_index[re.sub(r"\s+", " ", name.strip()).casefold()][cid] = mapping
    by_id = {}
    for doc in documents:
        key = doc.get("documentId")
        if not isinstance(key, str) or not key:
            raise ValueError("DOCUMENT_ID_REQUIRED")
        if key in by_id and by_id[key] != doc:
            raise ValueError("DOCUMENT_VERSION_CONFLICT")
        by_id[key] = doc
    documents = sorted(by_id.values(), key=lambda d: d["documentId"])
    parents = list(range(len(documents)))
    def root(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i
    seen = {}
    for i, doc in enumerate(documents):
        for key in document_identifiers(doc):
            # Documento de publicacao e registro de ensaio nunca sao duplicatas.
            key = (doc.get("documentType"), key)
            if key in seen:
                parents[root(i)] = root(seen[key])
            seen[key] = i
    groups = defaultdict(list)
    for i, doc in enumerate(documents):
        groups[root(i)].append(doc)
    records, conflicts, audit = [], [], []
    for group in groups.values():
        # Preferencia explicita de fonte para representacao, sem resolver divergencias.
        group.sort(key=lambda d: (d.get("source") != "PUBMED", d["documentId"]))
        first = group[0]
        record = {"document_id": first["documentId"], "document_type": first.get("documentType"),
                  "title": first.get("title"), "sources": sorted({d["source"] for d in group}),
                  "document_ids": [d["documentId"] for d in group],
                  "identifiers": sorted({i for d in group for i in document_identifiers(d)}),
                  "references": [{k: d.get(k) for k in ("documentId", "versionId", "version", "source", "contentHash", "license", "accessStatus")} for d in group]}
        links = [link for d in group for link in d.get("studyLinks", [])]
        confirmed = {str(link["study_id"]) for link in links if link.get("link_certainty") == "CONFIRMADO"}
        # Mesmo documento atribuido a varios estudos fica ambiguo ate curadoria.
        record["study_id"] = next(iter(confirmed)) if len(confirmed) == 1 else None
        record["study_link_status"] = "CONFIRMADO" if len(confirmed) == 1 else "AMBIGUO" if confirmed else "SEM_VINCULO"
        classifications = {(l.get("context"), l.get("purpose")) for l in links if l.get("link_certainty") == "CONFIRMADO" and l.get("screening_status") in {"INCLUIDO_NUCLEO", "INCLUIDO_SEM_RESULTADO", "CAMADA_COMPLEMENTAR"}}
        record["context"], record["purpose"] = next(iter(classifications)) if len(classifications) == 1 else ("NAO_CLASSIFICADO", None)
        record["screening_states"] = sorted({l.get("screening_status", "PENDENTE") for l in links})
        values = []
        for doc in group:
            metadata = doc.get("metadata", {})
            section = metadata.get("protocolSection", {})
            status = section.get("statusModule", {})
            design = section.get("designModule", {})
            enrollment = design.get("enrollmentInfo", {})
            count = enrollment.get("count")
            count = count if isinstance(count, int) and not isinstance(count, bool) and count >= 0 else None
            interventions = section.get("armsInterventionsModule", {}).get("interventions", [])
            # Normalizacao lexical; nao equivale a uma identidade quimica confirmada.
            substances = sorted({re.sub(r"\s+", " ", n).casefold() for intervention in interventions
                                 if intervention.get("type") in {"DRUG", "BIOLOGICAL"} and (n := text(intervention.get("name")))})
            entities = []
            for name in substances:
                matches = chemical_index.get(name, {})
                mapping = next(iter(matches.values())) if len(matches) == 1 else None
                entities.append({"reported_name": name, "name": (mapping.get("normalized_name") or mapping["published_name"]) if mapping else name,
                                 "pubchem_cid": mapping["pubchem_cid"] if mapping else None,
                                 "identity_status": "PUBCHEM_VINCULADO" if mapping else "AMBIGUO" if matches else "LEXICAL"})
            substances = sorted({e["name"] for e in entities})
            countries = sorted({text(l.get("country")) for l in section.get("contactsLocationsModule", {}).get("locations", []) if text(l.get("country"))})
            values.append({"publication_year": year(metadata.get("pub_year") or metadata.get("pubYear")),
                           "start_year": year(status.get("startDateStruct", {}).get("date")),
                           "recruitment": text(status.get("overallStatus")), "design": text(design.get("studyType")),
                           "phases": sorted(set(design.get("phases", []))),
                           "enrollment_estimated": count if enrollment.get("type") == "ESTIMATED" else None,
                           "enrollment_actual": count if enrollment.get("type") == "ACTUAL" else None,
                           "enrollment_unknown_type": count if enrollment.get("type") not in {"ESTIMATED", "ACTUAL"} else None,
                           "countries": countries, "substances": substances, "chemical_entities": entities,
                           "indexed_chemicals": metadata.get("chemicals", []),
                           "has_results": metadata.get("hasResults") if isinstance(metadata.get("hasResults"), bool) else None,
                           "language": text(metadata.get("language")), "journal": text(metadata.get("journal")),
                           "publication_types": sorted(set(metadata.get("publication_types", []))),
                           "referenced_pmids": sorted({identifier("PMID", ref.get("pmid")) for ref in section.get("referencesModule", {}).get("references", []) if ref.get("type") == "RESULT" and identifier("PMID", ref.get("pmid"))})})
        for field in values[0]:
            distinct = {json.dumps(v[field], sort_keys=True, ensure_ascii=False) for v in values if v[field] is not None and v[field] != []}
            if len(distinct) > 1:
                record[field] = [] if isinstance(values[0][field], list) else None
                conflicts.append({"document_id": record["document_id"], "field": field, "values": sorted(distinct)})
            else:
                record[field] = json.loads(next(iter(distinct))) if distinct else values[0][field]
        record["conflict_fields"] = sorted(c["field"] for c in conflicts if c["document_id"] == record["document_id"])
        records.append(record)
        if len(group) > 1:
            audit.append({"action": "EXACT_IDENTIFIER_DOCUMENT_DEDUP", "kept": first["documentId"], "members": record["document_ids"]})
    return sorted(records, key=lambda r: r["document_id"]), conflicts, audit


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


def save_figure(figure):
    figure.tight_layout()
    output = io.BytesIO()
    figure.savefig(output, format="png", dpi=120, metadata={"Software": SCRIPT_VERSION})
    figure.clear()
    return output.getvalue()


def charts(summary, records):
    files = {}
    if not records:
        return files
    fig = Figure(figsize=(10, 4)); ax = fig.subplots()
    for field, label in (("publication_year", "Ano de publicacao"), ("start_year", "Ano de inicio do ensaio")):
        rows = sorted((r for r in summary["temporal"] if r["field"] == field and r["category"] != MISSING), key=lambda r: int(r["category"]))
        if rows:
            ax.plot([int(r["category"]) for r in rows], [r["count"] for r in rows], marker=".", label=label)
    ax.set(title="Distribuicao temporal — eventos distintos", ylabel="Numero de registros", xlabel="Ano")
    if ax.lines: ax.legend()
    files["figures/temporal.png"] = save_figure(fig)
    for field in ("substances", "countries", "phases", "recruitment"):
        rows = sorted((r for r in summary["distributions"] if r["field"] == field), key=lambda r: (-r["count"], r["category"]))[:20]
        if rows:
            fig = Figure(figsize=(10, max(3, .3*len(rows)))); ax = fig.subplots()
            ax.barh([r["category"][:90] for r in rows], [r["count"] for r in rows]); ax.invert_yaxis()
            ax.set(title=f"{field}: ate 20 categorias por frequencia (tabela completa no CSV)", xlabel="Registros de ensaios")
            files[f"figures/{field}.png"] = save_figure(fig)
    trials = [r for r in records if r["document_type"] == "REGISTRO_ENSAIO"]
    fig = Figure(figsize=(11, 4)); axes = fig.subplots(1, 2)
    for axis, field, label in zip(axes, ("enrollment_estimated", "enrollment_actual"), ("Participantes previstos", "Participantes efetivos")):
        values = [r[field] for r in trials if r[field] is not None]
        if values: axis.hist(values, bins=min(15, max(1, len(values))))
        else: axis.text(.5, .5, "Sem dados", ha="center", transform=axis.transAxes)
        axis.set(title=f"{label} (n={len(values)}/{len(trials)})", xlabel="Participantes informados", ylabel="Registros")
    files["figures/enrollment.png"] = save_figure(fig)
    rows = summary["completeness"]
    if rows:
        labels = sorted({f"{r['source']} / {r['unit']}" for r in rows}); fields = sorted({r["field"] for r in rows})
        matrix = [[next((r["proportion"] if r["proportion"] is not None else float("nan") for r in rows if f"{r['source']} / {r['unit']}" == label and r["field"] == field), float("nan")) for field in fields] for label in labels]
        fig = Figure(figsize=(11, max(3, .6*len(labels)))); ax = fig.subplots()
        im = ax.imshow(matrix, aspect="auto", vmin=0, vmax=1, cmap="YlGnBu")
        ax.set_yticks(range(len(labels)), labels); ax.set_xticks(range(len(fields)), fields, rotation=45, ha="right")
        ax.set_title("Disponibilidade de metadados — celulas vazias nao se aplicam a esta tabela")
        fig.colorbar(im, ax=ax, label="Proporcao de preenchimento")
        files["figures/completeness.png"] = save_figure(fig)
    geography = Path(__file__).parent / "data" / "countries.geojson"
    if geography.exists():
        world = json.loads(geography.read_text(encoding="utf-8"))
        counts = {COUNTRY_ALIASES.get(r["category"], r["category"]): r["count"] for r in summary["distributions"] if r["field"] == "countries" and r["category"] != MISSING}
        fig = Figure(figsize=(12, 6)); ax = fig.subplots()
        maximum = max(counts.values(), default=1)
        matched = set()
        for feature in world["features"]:
            props = feature["properties"]
            names = [props.get(k) for k in ("ADMIN", "NAME_EN", "NAME_LONG", "NAME", "name")]
            name = next((n for n in names if n in counts), next((n for n in names if n), None))
            count = counts.get(name)
            if count is not None: matched.add(name)
            color = matplotlib.colormaps["Blues"](.2 + .8*count/maximum) if count is not None else "#ededed"
            geometry = feature["geometry"]
            polygons = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
            for polygon in polygons: ax.add_patch(Polygon(polygon[0], facecolor=color, edgecolor="#aaaaaa", linewidth=.2))
        ax.set(xlim=(-180, 180), ylim=(-60, 90), title="Paises de realizacao de ensaios; cinza: sem registro mapeado", xlabel="Longitude", ylabel="Latitude")
        fig.colorbar(matplotlib.cm.ScalarMappable(norm=matplotlib.colors.Normalize(0, maximum), cmap="Blues"), ax=ax, label="Registros por pais")
        files["figures/countries_map.png"] = save_figure(fig)
        summary["geography"] = {"matchedCountries": sorted(matched), "unmappedCountries": sorted(counts.keys()-matched), "source": "Natural Earth 1:110m, public domain", "hash": digest(geography.read_bytes())}
    return files


def flatten(row):
    return {k: json.dumps(v, ensure_ascii=False, sort_keys=True) if isinstance(v, (list, dict)) else v for k, v in row.items()}


def bundle(content):
    summary, records = analyze(content)
    files = Artifacts()
    files["dataset.json"] = content
    tables = {"dataset.csv": records, "documents.csv": records, "distributions.csv": summary["distributions"],
              "temporal.csv": summary["temporal"], "completeness.csv": summary["completeness"],
              "temporal_flags.csv": summary["temporalFlags"],
              "links.csv": summary["links"], "link_candidates.csv": summary["linkCandidates"],
              "conflicts.csv": summary["conflicts"], "enrollment.csv": summary["enrollment"],
              "transformations.csv": summary["transformations"],
              "studies.csv": json.loads(content).get("studies", []),
              "evidence_fields.csv": json.loads(content).get("scientificFields", []),
              "scientific_field_availability.csv": summary["scientificFieldAvailability"]}
    for name, rows in tables.items():
        columns = sorted({k for row in rows for k in row}) or ["status"]
        files[name] = csv_bytes([flatten(row) for row in rows], columns)
    reviewed = {"schemaVersion": "2.0", "dictionaryVersion": "descriptive-v2.0", "fields": FIELDS, "studies": json.loads(content).get("studies", [])}
    evidence_files = reviewed_bundle(json_bytes(reviewed))
    # As mesmas rotinas numericas e graficas sao usadas para os dados revisados.
    for name in ("gaps.csv", "traceability.csv"):
        files[name] = evidence_files[name]
    files["reviewed_completeness.csv"] = evidence_files["completeness.csv"]
    files["reviewed_distributions.csv"] = evidence_files["distributions.csv"]
    for name, data in evidence_files.items():
        if name.startswith("figures/"): files[name.replace("figures/", "figures/reviewed_")] = data
    for name, data in charts(summary, records).items():
        files[name] = data
    files["summary.json"] = json_bytes(summary)
    files["records.json"] = json_bytes(records)
    pilot = [{"document_id": r["document_id"], "sources": ";".join(r["sources"]), "title": r["title"],
              "document_type": r["document_type"], "identifiers": ";".join(r["identifiers"]),
              "eligibility_decision": "PENDENTE", "exclusion_reason": "", "context_reviewed": "", "purpose_reviewed": "",
              "preparation_validated": "PENDENTE", "reviewer": "", "reviewed_at": "", "notes": ""} for r in records[:50]]
    files["pilot_review.csv"] = csv_bytes(pilot, list(pilot[0]) if pilot else ["document_id", "preparation_validated"])
    images = "".join(f'<figure><img src="{html.escape(name)}" alt="{html.escape(name)}" style="max-width:100%"></figure>' for name in files if name.endswith(".png"))
    table = "".join(f"<tr><td>{html.escape(str(r['field']))}</td><td>{html.escape(str(r['category']))}</td><td>{r['count']}/{r['denominator']}</td></tr>" for r in summary["distributions"])
    files["report.html"] = (f'<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>DenguePharma — corpus</title><h1>Panorama do corpus coletado</h1><p>{html.escape(NOTICE)}</p>'
                            f'<p>Documentos: {len(records)}. Publicacoes: {summary["publicationCount"]}. Registros de ensaios: {summary["trialCount"]}. Estudos revisados: {summary["studyCount"]}.</p>'
                            + ('<p>Sem dados.</p>' if not records else '')
                            + f'<table><tr><th>Campo</th><th>Categoria</th><th>Contagem/denominador</th></tr>{table}</table>{images}</html>').encode("utf-8")
    script_files = [Path(__file__), Path(__file__).with_name("analysis.py")]
    geo = Path(__file__).parent / "data" / "countries.geojson"
    if geo.exists(): script_files.append(geo)
    files["reproduction_source.json"] = json_bytes({"package": "denguepharma_workers", "encoding": "base64", "files": {
        **{("data/" + p.name if p.suffix == ".geojson" else p.name): base64.b64encode(p.read_bytes()).decode("ascii") for p in script_files},
        "__init__.py": ""}, "notice": "Codigo-fonte e dados cartograficos desta execucao; dependencias no manifesto. Decodificar base64 preserva os bytes originais."})
    manifest = {"schemaVersion": "3.0", "dictionaryVersion": "corpus-v3.0", "scriptVersion": SCRIPT_VERSION,
                "inputHash": digest(content), "scriptHash": digest(b"".join(p.read_bytes() for p in script_files)),
                "sourceHashes": {p.name: digest(p.read_bytes()) for p in script_files},
                "dependencies": {"python": platform.python_version(), "pandas": pd.__version__, "matplotlib": matplotlib.__version__, "numpy": version("numpy"), "pillow": version("pillow")},
                "configuration": {"units": ["document", "trial_registry", "reviewed_study"], "normalization": "lexical_only", "missing": "explicit", "deduplication": "exact_identifier", "clinicalPreclinical": "separate"},
                "artifacts": {name: digest(value) for name, value in sorted(files.items())}}
    files["manifest.json"] = json_bytes(manifest)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            entry = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0)); entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, data)
    files["bundle.zip"] = output.getvalue()
    return files
