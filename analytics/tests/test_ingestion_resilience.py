"""Testes automatizados para a família de Ingestão e Resiliência de Fontes (REQ-ING).

Cobre os cenários de aceitação:
- ACC-ING-001 (REQ-ING-001): Registro formal de SearchRun com consulta, parâmetros e total de registros.
- ACC-ING-002 (REQ-ING-002): Idempotência e preservação de contagens de Study e DocumentVersion (T1).
- ACC-ING-003 (REQ-ING-003): Imutabilidade de snapshots da camada bronze e integridade por hash SHA-256.
- ACC-ING-004 (REQ-ING-004): Resiliência a rate limit (HTTP 429) e 5xx com Retry-After e sem duplicação de registros.
- ACC-ING-005 (REQ-ING-005): Ponto de checagem (checkpoint) permitindo retomada exata de coletas interrompidas.
- ACC-ING-007 (REQ-ING-007): Salvaguarda de propriedade intelectual: texto restrito a licenças abertas (T9).
- ACC-ING-009 (REQ-ING-009): Manifesto de dados de fontes externas com hash verificável.
"""

import pytest
from denguepharma_analytics.sources import (
    BronzeRawSnapshotStore,
    ImmutableSnapshotError,
    IngestionCheckpointManager,
    IngestionRepository,
    LicenseEnforcer,
    RateLimitError,
    ResilientFetcherWithBackoff,
    SearchRun,
    SourceDataManifest,
)


def test_req_ing_001_search_run_registration_and_exact_sum():
    """ACC-ING-001: Dado uma coleta no ClinicalTrials.gov com condição dengue,

    quando concluir, então o SearchRun existe e o total é igual à soma dos registros paginados.
    """
    source = "ClinicalTrials.gov"
    query = "dengue AND intervention"
    params = {"condition": "dengue", "type": "Interventional"}
    pages_data = [
        [{"id": f"NCT0000000{i}", "title": f"Study {i}"} for i in range(1, 6)],   # 5 registros
        [{"id": f"NCT0000000{i}", "title": f"Study {i}"} for i in range(6, 11)],  # 5 registros
        [{"id": f"NCT000000{i}", "title": f"Study {i}"} for i in range(11, 16)],  # 5 registros
    ]

    fetcher = ResilientFetcherWithBackoff()
    records, run = fetcher.fetch_all_pages(
        source=source,
        query=query,
        total_pages=3,
        fetch_page_fn=lambda p: pages_data[p - 1],
    )

    # Verificações de SearchRun
    assert run is not None
    assert run.source == "ClinicalTrials.gov"
    assert run.query == query
    assert run.status == "COMPLETED"
    assert run.finished_at is not None
    assert run.pages_completed == 3

    # Total é igual à soma exata dos registros paginados
    expected_sum = sum(len(p) for p in pages_data)
    assert len(records) == 15
    assert run.total_returned == expected_sum
    assert run.records_seen == expected_sum


def test_req_ing_002_idempotent_reimport_preserves_study_and_version_counts():
    """ACC-ING-002: Dado um NCT já importado, quando reimportar sem mudança,

    então as contagens de Study e de DocumentVersion ficam iguais (T1).
    """
    repo = IngestionRepository()

    raw_study_data = {
        "nctId": "NCT01614964",
        "briefTitle": "Trial of Celgosivir in Dengue",
        "phase": "PHASE1_PHASE2",
        "enrollment": 180,
    }

    # 1. Primeira importação
    res1 = repo.import_record(
        canonical_id="NCT01614964",
        doc_type="trial_registry",
        raw_content=raw_study_data,
    )
    assert res1["created_new_doc"] is True
    assert res1["created_new_study"] is True
    assert res1["created_new_version"] is True
    assert res1["total_studies"] == 1
    assert res1["total_versions"] == 1

    # 2. Reimportação sem alteração de conteúdo
    res2 = repo.import_record(
        canonical_id="NCT01614964",
        doc_type="trial_registry",
        raw_content=raw_study_data,
    )
    # Contagens de Study e DocumentVersion permanecem estritamente iguais
    assert res2["created_new_doc"] is False
    assert res2["created_new_study"] is False
    assert res2["created_new_version"] is False
    assert res2["total_studies"] == 1
    assert res2["total_versions"] == 1
    assert res2["current_version_no"] == 1

    # 3. Importação com alteração (status mudou de RECRUITING para COMPLETED)
    updated_study_data = dict(raw_study_data, overallStatus="COMPLETED")
    res3 = repo.import_record(
        canonical_id="NCT01614964",
        doc_type="trial_registry",
        raw_content=updated_study_data,
    )
    # Não cria novo Study, mas cria nova DocumentVersion (versão 2)
    assert res3["created_new_study"] is False
    assert res3["created_new_version"] is True
    assert res3["total_studies"] == 1
    assert res3["total_versions"] == 2
    assert res3["current_version_no"] == 2


def test_req_ing_003_bronze_immutable_snapshots_and_tamper_rejection():
    """ACC-ING-003: Dado um snapshot gravado, quando se tentar alterá-lo ou apagá-lo,

    então a operação é rejeitada e o hash recalculado coincide.
    """
    store = BronzeRawSnapshotStore()
    payload = b'{"protocolSection": {"identificationModule": {"nctId": "NCT01614964"}}}'

    # Gravação na camada bronze
    snapshot = store.save_snapshot(
        source="clinicaltrials",
        url="https://clinicaltrials.gov/api/v2/studies/NCT01614964",
        payload=payload,
        source_version="api_v2",
    )
    assert snapshot.snapshot_id is not None
    assert store.verify_integrity(snapshot.snapshot_id) is True

    # Tentativa de alteração é rejeitada
    with pytest.raises(ImmutableSnapshotError, match="não pode ser alterado"):
        store.update_snapshot(snapshot.snapshot_id, b'{"mutated": true}')

    # Tentativa de exclusão é rejeitada
    with pytest.raises(ImmutableSnapshotError, match="não pode ser apagado"):
        store.delete_snapshot(snapshot.snapshot_id)

    # O hash recalculado coincide exatamente
    assert store.verify_integrity(snapshot.snapshot_id) is True
    retrieved = store.get_snapshot(snapshot.snapshot_id)
    assert retrieved.payload == payload


def test_req_ing_004_rate_limit_resilience_and_deduplication():
    """ACC-ING-004: Dado um 429 simulado na página 3 de 10, quando a coleta continuar,

    então são recuperadas as 10 páginas, sem duplicatas.
    """
    # 10 páginas simuladas
    pages_dataset = {
        p: [{"id": f"DOC-PAGE{p}-REC{i}", "title": f"Doc {p}_{i}"} for i in range(1, 4)]
        for p in range(1, 11)
    }

    call_counts = {p: 0 for p in range(1, 11)}

    def mock_fetch(page: int):
        call_counts[page] += 1
        # Simula erro 429 na página 3 na primeira tentativa
        if page == 3 and call_counts[page] == 1:
            raise RateLimitError("Rate limit exceeded. Retry after 0.05 seconds", retry_after_seconds=0.05)
        return pages_dataset[page]

    fetcher = ResilientFetcherWithBackoff(max_retries=3, base_backoff=0.01)
    records, run = fetcher.fetch_all_pages(
        source="PubMed",
        query="dengue antiviral therapeutics",
        total_pages=10,
        fetch_page_fn=mock_fetch,
    )

    # Foram recuperadas todas as 10 páginas (3 registros cada = 30 registros)
    assert len(records) == 30
    assert run.pages_completed == 10
    assert run.total_returned == 30

    # Nenhuma duplicata existe
    rec_ids = [r["id"] for r in records]
    assert len(rec_ids) == len(set(rec_ids))

    # Página 3 foi tentada duas vezes (uma falha 429 e um sucesso após backoff)
    assert call_counts[3] == 2
    assert len(fetcher.telemetry_retries) == 1
    assert fetcher.telemetry_retries[0]["page"] == 3


def test_req_ing_005_checkpoint_resumption_from_interrupted_page():
    """ACC-ING-005: Dado uma coleta interrompida na página 5, quando reiniciar,

    então ela continua da página 5 (ou seja, inicia na página 6 sem reprocessar 1-5).
    """
    checkpoint_mgr = IngestionCheckpointManager()
    source = "PubMed"
    query = "dengue NS5 protease inhibitor"

    # Simula interrupção na página 5 (páginas 1 a 5 concluídas)
    checkpoint_mgr.save_checkpoint(
        source=source,
        query=query,
        last_page=5,
        records_collected=25,
    )

    fetcher = ResilientFetcherWithBackoff(checkpoint_manager=checkpoint_mgr)

    requested_pages = []

    def mock_fetch(page: int):
        requested_pages.append(page)
        return [{"id": f"DOC-PAGE{page}-REC{i}"} for i in range(1, 6)]

    # Retoma a coleta para um total de 8 páginas
    records, run = fetcher.fetch_all_pages(
        source=source,
        query=query,
        total_pages=8,
        fetch_page_fn=mock_fetch,
        resume_from_checkpoint=True,
    )

    # A coleta continuou a partir da página 6 (páginas 6, 7 e 8 requisitadas)
    assert requested_pages == [6, 7, 8]
    assert len(records) == 15  # 3 páginas * 5 registros


def test_req_ing_007_license_enforcement_and_unobtained_text():
    """ACC-ING-007: Dado um artigo sem licença de reuso, quando for importado,

    então só metadados são guardados e o status é “texto não obtido” (T9).
    """
    metadata = {
        "pmid": "31234567",
        "title": "Clinical Efficacy of Compound X in Dengue",
        "authors": ["Silva, J.", "Costa, M."],
        "year": 2023,
    }
    raw_fulltext = "Corpus completo do artigo com resultados detalhados..."

    # Cenário 1: Artigo sem licença ou com licença restritiva
    res_restricted = LicenseEnforcer.sanitize_document_ingestion(
        doc_id="DOC-FECHADO-01",
        license_name="All Rights Reserved",
        metadata=metadata,
        full_text=raw_fulltext,
    )
    assert res_restricted["access_status"] == "TEXTO_NAO_OBTIDO"
    assert res_restricted["full_text"] is None
    assert res_restricted["metadata"] == metadata

    # Cenário 2: Artigo com licença ausente (None)
    res_none = LicenseEnforcer.sanitize_document_ingestion(
        doc_id="DOC-SEM-LICENCA-02",
        license_name=None,
        metadata=metadata,
        full_text=raw_fulltext,
    )
    assert res_none["access_status"] == "TEXTO_NAO_OBTIDO"
    assert res_none["full_text"] is None

    # Cenário 3: Artigo com licença aberta (CC-BY 4.0)
    res_open = LicenseEnforcer.sanitize_document_ingestion(
        doc_id="DOC-OPEN-03",
        license_name="CC-BY-4.0",
        metadata=metadata,
        full_text=raw_fulltext,
    )
    assert res_open["access_status"] == "TEXTO_INTEGRAL_DISPONIVEL"
    assert res_open["full_text"] == raw_fulltext


def test_req_ing_009_source_data_manifest_with_verifiable_hashes():
    """ACC-ING-009: Dado uma execução concluída, quando o manifesto for gerado,

    então todas as fontes usadas constam com hash verificável.
    """
    manifest = SourceDataManifest()

    payload_ct = b'{"source": "clinicaltrials", "records": [1, 2, 3]}'
    payload_pubmed = b'{"source": "pubmed", "records": [4, 5]}'
    payload_chembl = b'{"source": "chembl", "records": [6]}'

    manifest.add_entry(
        source_name="ClinicalTrials.gov",
        url="https://clinicaltrials.gov/api/v2/studies",
        version="v2.1",
        parameters={"condition": "dengue"},
        raw_payload=payload_ct,
        total_records=3,
        license="Public Domain",
    )
    manifest.add_entry(
        source_name="PubMed / MEDLINE",
        url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
        version="eutils_v1",
        parameters={"term": "dengue AND clinical trial"},
        raw_payload=payload_pubmed,
        total_records=2,
        license="NLM Open Access",
    )
    manifest.add_entry(
        source_name="ChEMBL REST API",
        url="https://www.ebi.ac.uk/chembl/api/data",
        version="v33",
        parameters={"target": "Dengue virus NS5"},
        raw_payload=payload_chembl,
        total_records=1,
        license="CC-BY-SA-3.0",
    )

    doc = manifest.generate_manifest()
    assert doc["total_sources"] == 3
    assert len(doc["sources"]) == 3

    # Verificação de integridade por hash
    assert manifest.verify_entry_integrity("ClinicalTrials.gov", payload_ct) is True
    assert manifest.verify_entry_integrity("PubMed / MEDLINE", payload_pubmed) is True
    assert manifest.verify_entry_integrity("ChEMBL REST API", payload_chembl) is True

    # Se o payload for adulterado, a verificação deve falhar
    assert manifest.verify_entry_integrity("ClinicalTrials.gov", b'{"adulterado": true}') is False
