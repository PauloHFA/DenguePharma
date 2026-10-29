"""Enriquecimento privado somente de versoes exatas ja coletadas no PostgreSQL."""
import json
from uuid import UUID
from ..domain import digest
from ..sources.postgres import connect_read_only
from .workspace import clinical_text


def enrich(workspace):
    count=0
    with connect_read_only() as connection:
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        for document in workspace.input.data["documents"]:
            row=connection.execute("SELECT canonical_content,content_hash FROM document_version WHERE id=%s AND document_id=%s",(UUID(document["versionId"]),UUID(document["documentId"]))).fetchone()
            if not row or row["content_hash"]!=document["contentHash"] or digest(row["canonical_content"].encode())!=document["contentHash"]: raise ValueError("ORIGINAL_SOURCE_HASH_MISMATCH")
            workspace.attach_source(document,clinical_text(json.loads(row["canonical_content"]))); count+=1
    return {"workspace_id":workspace.key,"sources_verified":count,"mode":"read_only","scientific_decisions_created":0}
