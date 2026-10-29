"""Contratos do pipeline: nenhum dado cientifico e publicado automaticamente."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from typing import Any

from .extractor import CandidateField, extract_from_structured_metadata, validate_and_abstain

PIPELINE_VERSION = "rules-2"
PROMPT_HASH = hashlib.sha256(b"deterministic-metadata-rules-2:no-llm").hexdigest()


def source_text(metadata: dict[str, Any]) -> str:
    for name in ("text", "abstract"):
        if isinstance(metadata.get(name), str) and metadata[name].strip():
            return metadata[name]
    def values(node: Any):
        if isinstance(node, str):
            yield node
        elif isinstance(node, dict):
            for key in sorted(node):
                yield from values(node[key])
        elif isinstance(node, list):
            for child in node:
                yield from values(child)
    return "\n".join(values(metadata))


def extraction_payload(document_id: str, metadata: dict[str, Any]) -> dict[str, Any]:
    text = source_text(metadata)
    # Regras conservadoras: campos nao reconhecidos continuam ausentes, sem inferir eficacia.
    candidates = extract_from_structured_metadata({"abstract": text})
    enrollment = metadata.get("protocolSection", {}).get("designModule", {}).get("enrollmentInfo", {})
    if isinstance(enrollment.get("count"), int) and not isinstance(enrollment["count"], bool):
        # Numero estruturado nao tem trecho textual de suporte: preservar abstenção.
        candidates = [c for c in candidates if c.field_name != "sample_size"]
        candidates.append(CandidateField("sample_size", absence_status="NAO_EXTRAIDO"))
    fields = []
    for field in validate_and_abstain(text, candidates):
        value = asdict(field)
        quote = field.quoted_text
        # Mesma verificacao literal e posicao utilizada pelo backend.
        if field.absence_status == "PRESENTE" and (not quote or quote not in text):
            value.update(absence_status="INCERTO", normalized_value=None, quoted_text=None, locator=None)
        elif quote:
            start = text.index(quote)
            value["locator"] = f"char:{start}-{start + len(quote)}"
        fields.append({
            "fieldName": value["field_name"], "originalValue": value["original_value"],
            "normalizedValue": value["normalized_value"], "absenceStatus": value["absence_status"],
            "section": value["section"], "page": value["page"],
            "locator": value["locator"], "quotedText": value["quoted_text"],
        })
    return {"documentVersionId": document_id, "pipelineVersion": PIPELINE_VERSION,
            "modelProvider": "DETERMINISTIC_RULES", "modelVersion": PIPELINE_VERSION,
            "promptHash": PROMPT_HASH, "executionVariant": "rules", "schemaVersion": "1", "fields": fields}


def verify_document(content: bytes, expected_hash: str) -> dict[str, Any]:
    if hashlib.sha256(content).hexdigest() != expected_hash:
        raise ValueError("DOCUMENT_HASH_MISMATCH")
    value = json.loads(content)
    if not isinstance(value, dict):
        raise ValueError("DOCUMENT_SCHEMA_INVALID")
    return value
