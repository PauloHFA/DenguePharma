"""Leitura consistente da entrada canonica, sem mudar tabelas, usuarios ou migrations."""
from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID
import psycopg
from psycopg.rows import dict_row
from .snapshot import load_snapshot


def load_env(path: Path):
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def connect_read_only():
    # default_transaction_read_only protege inclusive a primeira transacao.
    return psycopg.connect(host=os.getenv("DB_HOST", "127.0.0.1"), port=int(os.getenv("DB_PORT", "5434")),
        dbname=os.getenv("DB_NAME", "denguepharma"), user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
        options="-c default_transaction_read_only=on", row_factory=dict_row, connect_timeout=10)


def from_postgres(analysis_id: str):
    key = UUID(analysis_id)
    with connect_read_only() as connection:
        with connection.transaction():
            connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            row = connection.execute("""
                SELECT a.id, s.canonical_content, s.content_hash,
                    EXISTS(SELECT 1 FROM analysis_publication p WHERE p.analysis_id=a.id) AS published
                FROM analysis_run a JOIN analysis_snapshot s ON s.id=a.snapshot_id WHERE a.id=%s
                """, (key,)).fetchone()
            if not row: raise ValueError("LEGACY_ANALYSIS_NOT_FOUND")
            content = row["canonical_content"].encode("utf-8")
            return load_snapshot(content, expected_hash=row["content_hash"], origin={
                "type": "legacy_postgresql_read_only", "analysis_id": str(key), "published_in_legacy": row["published"]})
