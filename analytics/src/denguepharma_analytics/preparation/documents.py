"""Preparacao v3 adaptada e validada por equivalencia; sem dependencia do worker legado."""
from __future__ import annotations
from collections import defaultdict
import json
import re
from ..identity.identifiers import text, year, identifier, document_identifiers

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
