from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from ..domain import digest


@dataclass(frozen=True)
class Snapshot:
    content: bytes
    data: dict
    input_hash: str
    origin: dict


def load_snapshot(content: bytes, *, expected_hash: str | None = None, origin: dict | None = None) -> Snapshot:
    actual = digest(content)
    if expected_hash and actual != expected_hash: raise ValueError("SNAPSHOT_HASH_MISMATCH")
    def reject_constants(value): raise ValueError("NON_FINITE_JSON")
    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise ValueError("DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    data = json.loads(content, parse_constant=reject_constants, object_pairs_hook=unique_keys)
    if not isinstance(data, dict) or data.get("schemaVersion") != "3.0" or data.get("dictionaryVersion") != "corpus-v3.0":
        raise ValueError("LEGACY_CORPUS_V3_REQUIRED")
    for name in ("documents", "studies"):
        if not isinstance(data.get(name), list): raise ValueError("INVALID_COLLECTION:" + name)
    for document in data["documents"]:
        for key in ("documentId", "versionId", "source", "documentType"):
            if not isinstance(document.get(key), str) or not document[key]: raise ValueError("MISSING_PROVENANCE:" + key)
        if not re.fullmatch(r"[a-f0-9]{64}", document.get("contentHash", "")): raise ValueError("INVALID_DOCUMENT_HASH")
        if document["documentType"] not in {"PUBLICACAO", "REGISTRO_ENSAIO", "DOCUMENTO_OFICIAL"}: raise ValueError("INVALID_DOCUMENT_TYPE")
        if not isinstance(document.get("metadata", {}), dict): raise ValueError("INVALID_METADATA")
    study_ids = {s.get("studyId") for s in data["studies"]}
    if None in study_ids: raise ValueError("MISSING_STUDY_ID")
    for field in data.get("scientificFields", []):
        if field.get("study_id") not in study_ids: raise ValueError("ORPHAN_SCIENTIFIC_FIELD")
        # O contrato v3 e de campos aprovados. Marcadores contrarios invalidam a entrada.
        if field.get("published") is False or field.get("review_status", "APROVADO") != "APROVADO":
            raise ValueError("UNREVIEWED_SCIENTIFIC_FIELD")
    return Snapshot(content, data, actual, origin or {"type": "legacy_snapshot_file"})


def from_file(path: Path, expected_hash: str | None = None):
    return load_snapshot(path.read_bytes(), expected_hash=expected_hash)
