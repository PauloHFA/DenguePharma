"""Chave de idempotência da extração (PDF, seção 13).

document_version_id + pipeline_version + model_version + prompt_hash + execution_variant
"""
import hashlib


def extraction_key(document_version_id: str, pipeline_version: str, model_version: str,
                   prompt_hash: str, execution_variant: str = "default") -> str:
    parts = (document_version_id, pipeline_version, model_version, prompt_hash, execution_variant)
    if any(not p for p in parts):
        raise ValueError("todos os componentes da chave de idempotência são obrigatórios")
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()

