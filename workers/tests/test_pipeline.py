import hashlib
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from minio.error import S3Error

from denguepharma_workers.pipeline import extraction_payload, source_text, verify_document
from denguepharma_workers.runtime import ApiError, ObjectStore, Worker


def test_pipeline_preserva_ausencias_e_posicoes_sem_publicar():
    metadata = {"abstract": "We randomized 50 adult patients with DENV-2."}
    output = extraction_payload("document", metadata)
    fields = {item["fieldName"]: item for item in output["fields"]}
    assert fields["sample_size"]["normalizedValue"] == "50"
    assert fields["serotype"]["quotedText"] == "DENV-2"
    assert fields["serotype"]["locator"] == "char:37-43"
    assert "published" not in fields["sample_size"]
    assert "absenceStatus" in fields["serotype"]
    missing = extraction_payload("other", {"abstract": "No numerical information."})
    assert all(f["absenceStatus"] != "PRESENTE" for f in missing["fields"])


def test_hash_precisa_corresponder_aos_bytes_originais():
    content = '{"abstract":"População DENV-2"}'.encode()
    assert verify_document(content, hashlib.sha256(content).hexdigest())["abstract"] == "População DENV-2"
    with pytest.raises(ValueError, match="HASH_MISMATCH"):
        verify_document(content + b" ", hashlib.sha256(content).hexdigest())


def test_chaves_de_json_nao_sao_tratadas_como_texto_cientifico():
    assert source_text({"protocolSection": {"module": {"briefSummary": "Study of DENV-1"}}}) == "Study of DENV-1"
    assert source_text({"text": "Full text", "abstract": "Summary"}) == "Full text"


def test_arquivo_existente_corrompido_nao_e_sobrescrito():
    store = ObjectStore.__new__(ObjectStore)
    store.client = Mock()
    store.read = Mock(return_value=b"corrupted")
    with pytest.raises(ValueError, match="STORED_OBJECT_CORRUPTED"):
        store.put_verified("key", b"original", hashlib.sha256(b"original").hexdigest())
    store.client.put_object.assert_not_called()


def test_arquivo_novo_e_lido_e_verificado_apos_upload():
    store = ObjectStore.__new__(ObjectStore)
    store.client = Mock()
    store.read = Mock(side_effect=[S3Error(response=None, code="NoSuchKey", message="missing", resource="key", request_id="req", host_id="host"), b"content"])
    assert store.put_verified("key", b"content", hashlib.sha256(b"content").hexdigest()) == b"content"
    store.client.put_object.assert_called_once()
    assert store.read.call_count == 2


def test_publicacao_sem_confirmacao_do_broker_nao_marca_outbox_como_publicada():
    worker = Worker.__new__(Worker)
    worker.api = Mock()
    worker.channel = Mock()
    worker.api.request.side_effect = [[{"event_id": "event", "relay_token": "token", "schema_version": 1, "priority": 0}], None]
    worker.channel.basic_publish.side_effect = RuntimeError("broker unavailable")
    with pytest.raises(RuntimeError):
        worker.dispatch()
    assert [call.args[0] for call in worker.api.request.call_args_list] == ["/outbox/claim?limit=20", "/outbox/event/fail"]


def test_reentrega_de_job_concluido_nao_executa_extracao():
    worker = Worker.__new__(Worker)
    worker.api = Mock()
    worker.channel = Mock()
    worker.store = Mock()
    worker.channel.basic_get.return_value = (SimpleNamespace(delivery_tag=1), None, json.dumps({"eventId": "d90863a4-c8df-4df1-a427-cff5e8374451", "schemaVersion": 1}).encode())
    worker.api.request.return_value = {"state": "COMPLETED", "jobId": "job"}
    assert worker.consume_one()
    worker.channel.basic_ack.assert_called_once_with(1)
    worker.store.put_verified.assert_not_called()
    assert worker.api.request.call_count == 1


def test_mensagem_invalida_vai_para_quarentena_do_broker():
    worker = Worker.__new__(Worker)
    worker.api = Mock()
    worker.channel = Mock()
    worker.channel.basic_get.return_value = (SimpleNamespace(delivery_tag=8), None, b'{"eventId":"not-a-uuid"}')
    worker.consume_one()
    worker.channel.basic_nack.assert_called_once_with(8, requeue=False)
    worker.api.request.assert_not_called()
