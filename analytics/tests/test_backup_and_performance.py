"""Testes para integridade de backup/restauração por hash e validação de SLO de latência p95.

Cobre formalmente:
- REQ-OPS-007 (ACC-OPS-007 / RNF-02): Backup e restauração testada em ambiente limpo com
  conferência estrita por hash de metadados e documentos referenciados.
- REQ-OPS-008 (ACC-OPS-008 / RNF-06): SLO de consultas usuais com p95 <= 2.0s em 10 mil registros
  e 10 usuários simultâneos, medindo isoladamente tempo analítico de banco.
"""

from __future__ import annotations

import hashlib
import sqlite3
import pytest
from denguepharma_analytics.ops.backup_and_performance import (
    BackupIntegrityError,
    BackupRestoreManager,
    PerformanceBenchmarker,
)


@pytest.fixture
def source_db():
    conn = sqlite3.connect(":memory:")
    with conn:
        conn.execute("""
            CREATE TABLE document_version (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                version_no INTEGER NOT NULL,
                content_hash TEXT NOT NULL,
                origin TEXT NOT NULL
            )
        """)
    yield conn
    conn.close()


@pytest.mark.requirement("REQ-OPS-007")
def test_backup_and_restore_in_clean_environment_verifies_hashes(source_db):
    """Cobre ACC-OPS-007: Dado um backup, quando restaurado em ambiente limpo,

    então metadados e documentos referenciados conferem estritamente por hash.
    """
    # 1. Popula banco de origem
    doc1_content = b"Clinical trial report for Celgosivir in dengue infection"
    doc1_hash = hashlib.sha256(doc1_content).hexdigest()

    doc2_content = b"Balapiravir phase II randomized evaluation notes"
    doc2_hash = hashlib.sha256(doc2_content).hexdigest()

    with source_db:
        source_db.execute(
            "INSERT INTO document_version VALUES ('doc-1', 'D1', 1, ?, 'PubMed')",
            (doc1_hash,),
        )
        source_db.execute(
            "INSERT INTO document_version VALUES ('doc-2', 'D2', 1, ?, 'ClinicalTrials.gov')",
            (doc2_hash,),
        )

    doc_store = {
        "doc-1": doc1_content,
        "doc-2": doc2_content,
    }

    # 2. Cria o pacote de backup
    backup_pkg = BackupRestoreManager.create_backup_package(source_db, doc_store)
    assert backup_pkg["manifest"]["documents_count"] == 2

    # 3. Restaura em ambiente totalmente limpo (nova conexão em memória vazia)
    clean_target = sqlite3.connect(":memory:")
    restore_result = BackupRestoreManager.restore_and_verify(backup_pkg, clean_target)

    assert restore_result["verified"] is True
    assert restore_result["verified_documents_count"] == 2
    assert restore_result["status"] == "RESTORE_VERIFIED_SUCCESS"

    # Confere dados no banco restaurado
    rows = clean_target.execute("SELECT id, content_hash FROM document_version ORDER BY id").fetchall()
    assert len(rows) == 2
    assert rows[0] == ("doc-1", doc1_hash)
    assert rows[1] == ("doc-2", doc2_hash)

    clean_target.close()


@pytest.mark.requirement("REQ-OPS-007")
def test_restore_rejects_corrupted_document_or_metadata():
    """Valida que qualquer alteração de bit ou hash corrompido é rejeitado com BackupIntegrityError."""
    source_db = sqlite3.connect(":memory:")
    with source_db:
        source_db.execute("CREATE TABLE document_version (id TEXT PRIMARY KEY, content_hash TEXT)")
        source_db.execute("INSERT INTO document_version VALUES ('doc-x', 'hash_original')")

    doc_store = {"doc-x": b"Original unmodified content"}
    pkg = BackupRestoreManager.create_backup_package(source_db, doc_store)

    # 1. Simula corrupção de arquivo (payload alterado em trânsito)
    corrupted_pkg = dict(pkg)
    corrupted_pkg["documents"] = {
        "doc-x": {
            "size_bytes": 10,
            "content_hash": pkg["documents"]["doc-x"]["content_hash"],
            "data": "Tampered content that does not match original hash",
        }
    }

    clean_db = sqlite3.connect(":memory:")
    with pytest.raises(BackupIntegrityError) as exc_info:
        BackupRestoreManager.restore_and_verify(corrupted_pkg, clean_db)
    assert "Corrupcao no documento" in str(exc_info.value)

    # 2. Simula corrupção do dump SQL
    corrupted_dump_pkg = dict(pkg)
    corrupted_dump_pkg["metadata_dump"] = "CORRUPTED SQL DUMP"
    with pytest.raises(BackupIntegrityError) as exc_info2:
        BackupRestoreManager.restore_and_verify(corrupted_dump_pkg, clean_db)
    assert "Corrupcao de metadados" in str(exc_info2.value)

    clean_db.close()
    source_db.close()


@pytest.mark.requirement("REQ-OPS-008")
def test_slo_workload_latency_p95_under_2_seconds():
    """Cobre ACC-OPS-008: Dado a carga de referência (10 mil registros e 10 usuários simultâneos),

    quando executada, então o p95 é igual ou menor que 2.0 segundos.
    """
    bench_db = sqlite3.connect(":memory:")
    PerformanceBenchmarker.populate_reference_dataset(bench_db, target_records=10000)

    # Verifica contagem de registros
    count = bench_db.execute("SELECT count(*) FROM clinical_evidence_benchmark").fetchone()[0]
    assert count == 10000

    # Executa bateria de 200 consultas simulando 10 usuários simultâneos
    results = PerformanceBenchmarker.execute_workload_benchmark(
        conn=bench_db,
        simulated_users=10,
        queries_per_user=20,
    )

    assert results["total_records"] == 10000
    assert results["total_queries_executed"] == 200
    assert results["slo_met_p95_under_2s"] is True
    assert results["p95_sec"] <= 2.0  # ACC-OPS-008 formal
    assert results["ai_inference_isolated"] is True

    bench_db.close()

