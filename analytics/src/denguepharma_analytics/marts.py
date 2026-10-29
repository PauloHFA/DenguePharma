"""Schemas explicitos: tabela vazia mantem tipos e nao vira metrica perfeita."""
from __future__ import annotations

import json
import pyarrow as pa
from .domain import FIELDS
from .analyses.reviewed import analyze as reviewed_analysis
from .domain import json_bytes

TYPES = {"s": pa.string(), "i": pa.int64(), "f": pa.float64(), "b": pa.bool_()}


def schema(fields):
    return pa.schema([(name, TYPES[type_]) for name, type_ in fields])


DOCUMENT_FIELDS = [(n, "s") for n in ("document_id", "document_type", "title", "study_id", "study_link_status", "context", "purpose", "recruitment", "design")]
DOCUMENT_FIELDS += [(n, "i") for n in ("publication_year", "start_year", "enrollment_estimated", "enrollment_actual", "enrollment_unknown_type")]
DOCUMENT_FIELDS += [("has_results", "b")]
DOCUMENT_FIELDS += [(n + "_json", "s") for n in ("sources", "identifiers", "countries", "substances", "phases", "screening_states", "conflict_fields", "references", "chemical_entities")]
PANORAMA_FIELDS = [(n, "s") for n in ("study_id", "layer", "context", "context_status", "purpose", "purpose_status")]
PANORAMA_FIELDS += [(n, "s") for field in FIELDS for n in (field, field + "_status")]
PANORAMA_FIELDS += [("reassessment_pending", "b"), ("sponsor_name", "s"), ("sponsor_type", "s")]

SCHEMAS = {
    "silver_documents": schema(DOCUMENT_FIELDS),
    "silver_document_versions": schema([(n, "s") for n in ("document_id", "version_id", "source", "content_hash", "retrieved_at", "license", "access_status")] + [("version", "i")]),
    "silver_study_links": schema([(n, "s") for n in ("document_id", "study_id", "certainty", "screening_status", "context", "purpose")]),
    "silver_identifiers": schema([(n, "s") for n in ("document_id", "kind", "value")]),
    "silver_scientific_fields": schema([(n, "s") for n in ("field_id", "study_id", "field_name", "value", "status", "document_id", "document_version_id", "content_hash", "source", "license", "locator")]),
    "mart_panorama": schema(PANORAMA_FIELDS),
    "corpus_distributions": schema([(n, "s") for n in ("field", "category", "unit", "population")] + [("count", "i"), ("denominator", "i"), ("proportion", "f"), ("overlapping", "b")]),
    "corpus_temporal": schema([(n, "s") for n in ("field", "category", "unit", "population")] + [("count", "i"), ("denominator", "i"), ("proportion", "f"), ("overlapping", "b")]),
    "corpus_completeness": schema([(n, "s") for n in ("source", "field", "unit", "review_status")] + [(n, "i") for n in ("present", "applicable", "total", "conflicts", "not_applicable", "missing")] + [("proportion", "f")]),
    "corpus_enrollment": schema([("field", "s"), ("unit", "s")] + [(n, "i") for n in ("available", "denominator", "missing", "min", "max")] + [(n, "f") for n in ("median", "q1", "q3")] + [("sumsParticipants", "b")]),
    "corpus_links": schema([(n, "s") for n in ("trial_document_id", "publication_document_id", "study_id", "status")]),
    "corpus_link_candidates": schema([(n, "s") for n in ("trial_document_id", "publication_document_id", "identifier", "status")]),
    "corpus_temporal_flags": schema([("document_id", "s"), ("publication_year", "i"), ("status", "s")]),
    "reviewed_distributions": schema([(n, "s") for n in ("layer", "context", "field", "category", "status")] + [("count", "i"), ("denominator", "i"), ("proportion", "f")]),
    "reviewed_completeness": schema([("context", "s"), ("field", "s")] + [(n, "i") for n in ("present", "applicable", "total")] + [("proportion", "f"), ("states_json", "s")]),
    "reviewed_gaps": schema([(n, "s") for n in ("map", "layer", "context", "substance", "category")] + [("count", "i"), ("denominator", "i")]),
    "reviewed_traceability": schema([("metric", "s"), ("numerator", "i"), ("denominator", "i"), ("proportion", "f")]),
    "scientific_field_availability": schema([("context", "s"), ("field", "s")] + [(n, "i") for n in ("present", "applicable", "total")] + [("proportion", "f"), ("states_json", "s")]),
}
from .clinical.models import GROUP_FIELDS
SCHEMAS.update({
    "publication_reference_links": schema([(n,"s") for n in ("link_id","trial_id","nct_id","reference_type","pmid","pmid_state","status","source_url","publication_document_ids_json","publication_references_json","trial_references_json","observations_json")]+[("automatically_confirmed","b")]),
    "publication_reference_coverage": schema([("reference_type","s")]+[(n,"i") for n in ("total_registry_units","registry_units_with_references","registry_units_with_valid_pmid","registry_units_with_candidate","distinct_valid_pmids","valid_pmids_in_corpus","not_retrieved_pmids","missing_or_invalid_entries")]+[(n,"f") for n in ("registry_reference_proportion","pmid_coverage_proportion")]),
    "publication_reference_missing": schema([(n,"s") for n in ("pmid","source_url","trial_ids_json","reference_types_json","trial_references_json","status")]),
    "reporting_registry": schema([(n,"s") for n in ("trial_id","nct_id","cutoff_date","overall_status","overall_status_state","has_results_state","result_category","interval_status","flags_json","references_json","observations_json")]+[("has_results","b"),("interval_days","i")]+[(f+suffix,"s") for f in ("primary","results","last_update") for suffix in ("_date","_precision","_type","_state")]),
    "reporting_availability": schema([(n,"s") for n in ("field","category","unit")]+[("count","i"),("denominator","i"),("proportion","f")]),
    "reporting_results_by_status": schema([(n,"s") for n in ("overall_status","result_category","unit")]+[("count","i"),("denominator","i"),("proportion","f")]),
    "reporting_intervals": schema([(n,"s") for n in ("origin","endpoint","unit")]+[(n,"i") for n in ("observed","completed","total_trials","min","max")]+[(n,"f") for n in ("median","q1","q3")]+[("censoring","b")]),
    "corpus_sponsor_trials": schema([(n,"s") for n in ("trial_id","nct_id","identifier_status","sponsor_name","sponsor_name_status","sponsor_type","sponsor_type_status","document_ids_json","observed_names_json","observed_types_json","references_json","observations_json")]),
    "corpus_sponsor_distributions": schema([(n,"s") for n in ("field","category","status","unit")]+[("count","i"),("denominator","i"),("proportion","f")]),
    "corpus_sponsor_completeness": schema([(n,"s") for n in ("field","unit")]+[(n,"i") for n in ("present","missing","conflicts","denominator")]+[("proportion","f")]),
    "calibration_documents": schema([(n,"s") for n in ("document_id","study_id","document_type","title","source_url","signal_status","review_status","sources_json","identifiers_json","signal_codes_json","signals_json","interventions_json","references_json")]),
    "calibration_signals": schema([(n,"s") for n in ("source","code","label")]+[(n,"i") for n in ("count","denominator")]+[("proportion","f"),("overlapping","b")]),
    "calibration_intervention_types": schema([("intervention_type","s"),("count","i"),("denominator","i"),("proportion","f"),("overlapping","b")]),
    "calibration_searches": schema([(n,"s") for n in ("source","query","status","executed_at","finished_at")]+[(n,"i") for n in ("reported_total","retrieved_documents")]+[("retrieved_fraction","f")]),
    "clinical_screening": schema([(n,"s") for n in ("study_id","basis_hash","status","classification_json")]),
    "clinical_results": schema([(n,"s") for n in dict.fromkeys(["study_id","result_id","decision_id","comparison_id","outcome_domain",*GROUP_FIELDS,"effect_type","state","method","note","limitations","support_care","risk_of_bias","risk_of_bias_reason","risk_of_bias_instrument"])]+[(n,"f") for n in ("estimate","ci_low","ci_high","confidence_level")]+[(n,"i") for n in ("treatment_n","control_n","participants_comparison")]+[(n,"s") for n in ("treatment_json","control_json","absence_states_json","risk_of_bias_domains_json","document_result_ids_json")]),
    "clinical_synthesis": schema([(n,"s") for n in ("scope_id","scope_json","result_set_hash","category","judgment_id","judgment_json","result_ids_json","study_ids_json")]+[("study_count","i")]),
    "clinical_references": schema([(n,"s") for n in ("result_id","field","version_id","document_id","content_hash","text_hash")]+[(n,"i") for n in ("start","end")]),
    "clinical_conflicts": schema([(n,"s") for n in ("key","result_ids_json","status")]),
    "clinical_absences": schema([(n,"s") for n in ("intervention","population","reason","basis_hash","decision_id","category")]),
})
PUBLIC_TABLES = frozenset(name for name in SCHEMAS if not name.startswith("silver_")) | {"corpus_documents"}
SCHEMAS["corpus_documents"] = SCHEMAS["silver_documents"]


def normalize_rows(rows, definition):
    result = []
    for row in rows:
        item = {}
        for field in definition:
            name = field.name
            if name.endswith("_json"):
                raw = row.get(name[:-5])
                item[name] = json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(",", ":")) if raw is not None else None
            else:
                item[name] = row.get(name)
        result.append(item)
    # Ordem canonica de todas as linhas; sem ordenar pelo hash aleatorio de processo.
    return sorted(result, key=lambda row: json.dumps(row, sort_keys=True, ensure_ascii=False, allow_nan=False))


def build_tables(snapshot, summary, records):
    versions, links, identifiers = [], [], []
    for document in snapshot["documents"]:
        versions.append({"document_id": document["documentId"], "version_id": document["versionId"], "version": document.get("version"),
            "source": document["source"], "content_hash": document["contentHash"], "retrieved_at": document.get("retrievedAt"),
            "license": document.get("license"), "access_status": document.get("accessStatus")})
        for link in document.get("studyLinks", []):
            links.append({"document_id": document["documentId"], "study_id": link.get("study_id"), "certainty": link.get("link_certainty"),
                          "screening_status": link.get("screening_status"), "context": link.get("context"), "purpose": link.get("purpose")})
    for record in records:
        for identifier in record["identifiers"]:
            kind, value = identifier.split(":", 1)
            identifiers.append({"document_id": record["document_id"], "kind": kind, "value": value})
    _, reviewed = reviewed_analysis(json_bytes({"schemaVersion": "2.0", "dictionaryVersion": "descriptive-v2.0", "fields": FIELDS, "studies": snapshot["studies"]}))
    datasets = {"silver_documents": records, "silver_document_versions": versions, "silver_study_links": links,
        "silver_identifiers": identifiers, "silver_scientific_fields": snapshot.get("scientificFields", []),
        "mart_panorama": reviewed, "corpus_documents": records,
        "corpus_distributions": summary["distributions"], "corpus_temporal": summary["temporal"], "corpus_completeness": summary["completeness"],
        "corpus_enrollment": summary["enrollment"], "corpus_links": summary["links"], "corpus_link_candidates": summary["linkCandidates"],
        "corpus_temporal_flags": summary["temporalFlags"], "reviewed_distributions": summary["reviewed"]["distributions"],
        "reviewed_completeness": summary["reviewed"]["completeness"], "reviewed_gaps": summary["reviewed"]["gaps"],
        "reviewed_traceability": summary["reviewed"]["traceability"], "scientific_field_availability": summary["scientificFieldAvailability"]}
    from .clinical.analysis import datasets as clinical_datasets
    datasets.update(clinical_datasets(snapshot.get("clinical")))
    from .clinical.calibration import analyze as calibration_analysis
    _,calibration_tables=calibration_analysis(snapshot,records)
    datasets.update(calibration_tables)
    from .analyses.sponsors import analyze as sponsor_analysis
    _,sponsor_tables=sponsor_analysis(snapshot)
    datasets.update(sponsor_tables)
    from .analyses.reporting import analyze as reporting_analysis
    _,reporting_tables=reporting_analysis(snapshot)
    datasets.update(reporting_tables)
    from .analyses.publication_refs import analyze as publication_analysis
    _,publication_tables=publication_analysis(snapshot)
    datasets.update(publication_tables)
    return {name: pa.Table.from_pylist(normalize_rows(datasets[name], definition), schema=definition) for name, definition in SCHEMAS.items()}
