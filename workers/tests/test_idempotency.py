import pytest

from denguepharma_workers.idempotency import extraction_key


def test_chave_estavel_para_mesma_entrada():
    a = extraction_key("dv1", "p1", "m1", "ph")
    assert a == extraction_key("dv1", "p1", "m1", "ph")


def test_outro_modelo_gera_nova_chave():
    assert extraction_key("dv1", "p1", "m1", "ph") != extraction_key("dv1", "p1", "m2", "ph")


def test_variante_de_execucao_altera_chave():
    assert extraction_key("dv1", "p1", "m1", "ph") != extraction_key("dv1", "p1", "m1", "ph", "ablation")


def test_componente_vazio_e_rejeitado():
    with pytest.raises(ValueError):
        extraction_key("dv1", "", "m1", "ph")

