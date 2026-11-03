import copy
import importlib.util
import json
from pathlib import Path
import os
import subprocess
import sys

import duckdb
from fastapi.testclient import TestClient
import psycopg
import pytest

from denguepharma_analytics.api import create_app
from denguepharma_analytics.domain import digest
from denguepharma_analytics.sources.snapshot import load_snapshot
from denguepharma_analytics.preparation.documents import prepare
from denguepharma_analytics.analyses.diagnostics import analyze
from denguepharma_analytics.storage import export, publish, query_table, verify_run
from conftest import legacy_imports


@pytest.mark.requirement("REQ-MIG-001")
def test_postgres_read_only(monkeypatch, snapshot):
    from denguepharma_analytics.sources import postgres
    calls = []
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def transaction(self): return self
        def execute(self, sql, params=None): calls.append((sql, params)); return self
        def fetchone(self): return {"canonical_content": snapshot.content.decode(), "content_hash": snapshot.input_hash, "published": True}
    def connect(**kwargs): calls.append(kwargs); return Connection()
    monkeypatch.setenv("DB_USER", "fixture"); monkeypatch.setenv("DB_PASSWORD", "fixture-secret")
    monkeypatch.setattr(postgres.psycopg, "connect", connect)
    result = postgres.from_postgres("5dc0c29f-234e-4ec4-8f32-91459358b472")
    assert calls[0]["options"] == "-c default_transaction_read_only=on"
    assert "REPEATABLE READ READ ONLY" in calls[1][0]
    assert result.content == snapshot.content
    assert "fixture-secret" not in json.dumps(result.origin)


@pytest.mark.requirement("REQ-MIG-001", "REQ-MIG-002")
def test_live_postgres_read_only():
    if os.getenv("ANALYTICS_LIVE_POSTGRES") != "true": pytest.skip("Defina ANALYTICS_LIVE_POSTGRES=true para a verificacao local sem escrita")
    from denguepharma_analytics.sources.postgres import connect_read_only, from_postgres, load_env
    load_env(Path(__file__).resolve().parents[2] / ".env")
    with connect_read_only() as connection:
        assert connection.execute("SHOW transaction_read_only").fetchone()["transaction_read_only"] == "on"
        with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
            connection.execute("UPDATE analysis_snapshot SET content_hash=content_hash WHERE false")
    result = from_postgres("5dc0c29f-234e-4ec4-8f32-91459358b472")
    assert result.input_hash == "6cd0c7c07456e66a70ecbe3aa49de40c2e11977449177edde68f8af53fcf264e"
    assert len(result.data["documents"]) == 50 and result.data["studies"] == []
    legacy_prepare, legacy_analyze = legacy_imports()
    assert prepare(result.data) == legacy_prepare(result.data)
    current, _ = analyze(result.content); previous, _ = legacy_analyze(result.content)
    current["reviewed"].pop("scriptVersion"); previous["reviewed"].pop("scriptVersion")
    assert current == previous


@pytest.mark.requirement("REQ-MIG-002", "REQ-MIG-012")
def test_provenance_and_atomicity(tmp_path, snapshot):
    manifest = export(snapshot, tmp_path)
    assert (tmp_path / "bronze" / snapshot.input_hash / "snapshot.json").read_bytes() == snapshot.content
    assert manifest["tables"]["silver_document_versions"]["rows"] == 3
    assert manifest["tables"]["silver_documents"]["rows"] == 2
    assert manifest["tables"]["mart_panorama"]["rows"] == 0
    assert export(snapshot, tmp_path) == manifest
    file = tmp_path / "runs" / manifest["run_id"] / "gold" / "corpus_documents.parquet"
    file.write_bytes(b"alterado")
    with pytest.raises(ValueError, match="HASH_MISMATCH"): export(snapshot, tmp_path)
    assert file.read_bytes() == b"alterado"
    assert not list(tmp_path.glob("analytics-*"))


@pytest.mark.requirement("REQ-MIG-003")
def test_legacy_equivalence(snapshot):
    legacy_prepare, legacy_analyze = legacy_imports()
    assert prepare(snapshot.data) == legacy_prepare(snapshot.data)
    actual, records = analyze(snapshot.content); expected, expected_records = legacy_analyze(snapshot.content)
    # A versao do modulo novo e distinta; os resultados cientificos devem permanecer iguais.
    actual["reviewed"].pop("scriptVersion"); expected["reviewed"].pop("scriptVersion")
    assert records == expected_records and actual == expected
    assert actual["documentCount"] == 2 and actual["publicationCount"] == 1 and actual["trialCount"] == 1
    assert actual["studyCount"] == 0
    assert next(r for r in actual["enrollment"] if r["field"] == "enrollment_actual")["median"] == 0


@pytest.mark.requirement("REQ-MIG-003", "REQ-MIG-004")
def test_reviewed_conflicts_missing_and_contexts(tmp_path, snapshot):
    data = copy.deepcopy(snapshot.data)
    data["studies"] = [{"studyId": key, "context": context, "purpose": "TRATAMENTO", "fields": {
        "substance": {"status": "PRESENTE", "value": "Compound"}, "design": {"status": "CONFLITO"},
        "phase": {"status": "NAO_APLICAVEL"}, "serotype": {"status": "SEM_REVISAO"}}} for key, context in (("s1", "HUMANO"), ("s2", "IN_VITRO"))]
    content = json.dumps(data).encode(); _, legacy = legacy_imports()
    actual, _ = analyze(content); expected, _ = legacy(content)
    actual["reviewed"].pop("scriptVersion"); expected["reviewed"].pop("scriptVersion")
    assert actual == expected
    manifest = export(load_snapshot(content), tmp_path); publish(tmp_path, manifest["run_id"])
    rows = query_table(tmp_path, manifest["run_id"], "mart_panorama")["rows"]
    assert {r["layer"] for r in rows} == {"CLINICO", "PRE_CLINICO"}
    assert all(r["design_status"] == "CONFLITO" and r["serotype_status"] == "SEM_REVISAO" for r in rows)


@pytest.mark.requirement("REQ-MIG-004")
def test_reproducible_marts(tmp_path, snapshot):
    first = export(snapshot, tmp_path / "a"); second = export(snapshot, tmp_path / "b")
    assert first["run_id"] == second["run_id"]
    for name, info in first["tables"].items():
        assert info == second["tables"][name]
        assert first["artifacts"][info["file"]] == second["artifacts"][info["file"]]
    with duckdb.connect(str(tmp_path / "a" / "runs" / first["run_id"] / "analytics.duckdb"), read_only=True) as db:
        assert db.execute("SELECT count(*) FROM mart_panorama").fetchone()[0] == 0
        assert len(db.execute("DESCRIBE mart_panorama").fetchall()) > 10
        assert db.execute("SELECT count(*) FROM corpus_documents").fetchone()[0] == 2
        with pytest.raises(duckdb.InvalidInputException): db.execute("CREATE TABLE forbidden(i INTEGER)")


@pytest.mark.requirement("REQ-MIG-005")
def test_public_api(tmp_path, snapshot):
    manifest = export(snapshot, tmp_path); run = manifest["run_id"]; client = TestClient(create_app(tmp_path))
    assert client.get("/api/public/analyses").json() == []
    assert client.get(f"/api/public/analyses/{run}").status_code == 404
    publish(tmp_path, run)
    assert client.get("/api/public/analyses").json()[0]["document_count"] == 2
    rows = client.get(f"/api/public/analyses/{run}/tables/corpus_documents?source=PUBMED").json()
    assert rows["total"] == 1 and rows["rows"][0]["document_type"] == "PUBLICACAO"
    assert client.get(f"/api/public/analyses/{run}/tables/corpus_documents?limit=1001").status_code == 422
    assert client.get(f"/api/public/analyses/{run}/tables/corpus_temporal?source=PUBMED").status_code == 422
    assert client.get(f"/api/public/analyses/{run}/artifacts?name=gold/mart_panorama.parquet").status_code == 200
    assert client.get(f"/api/public/analyses/{run}/artifacts?name=corpus_documents.csv").status_code == 200
    assert client.post(f"/api/public/analyses/{run}", json={}).status_code == 405
    assert client.post("/api/analyses/corpus", json={}).status_code == 404


@pytest.mark.requirement("REQ-MIG-011")
def test_public_privacy(prepared):
    root, manifest = prepared; run = manifest["run_id"]; client = TestClient(create_app(root))
    for path in (f"/{run}", f"/{run}/summary", f"/{run}/tables/corpus_documents", f"/{run}/artifacts?name=corpus_documents.csv"):
        response = client.get("/api/public/analyses"+path)
        assert response.status_code == 200
        assert not any(marker in response.text for marker in ("PRIVATE_FULLTEXT", "PRIVATE_CONTACT", "PRIVATE_KEY"))
    for name in ("../summary.json", "analytics.duckdb", "silver/silver_scientific_fields.parquet", "snapshot.json", "bronze/snapshot.json"):
        assert client.get(f"/api/public/analyses/{run}/artifacts", params={"name": name}).status_code == 404
    assert client.get(f"/api/public/analyses/{run}/tables/silver_documents").status_code == 404


@pytest.mark.requirement("REQ-MIG-008")
def test_independent_runtime(prepared):
    root, _ = prepared
    command = [sys.executable, "-c", "from fastapi.testclient import TestClient; from pathlib import Path; from denguepharma_analytics.api import create_app; c=TestClient(create_app(Path(__import__('sys').argv[1]))); assert c.get('/api/public/analyses').json()[0]['document_count']==2; assert 'denguepharma_workers' not in __import__('sys').modules", str(root)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    from denguepharma_analytics.api import CAPABILITIES
    assert CAPABILITIES["curation"]["state"] == "clinical_protected_legacy_auth"


@pytest.mark.requirement("REQ-MIG-010")
def test_capabilities():
    capabilities = TestClient(create_app()).get("/api/capabilities").json()
    assert capabilities["axes"]["A"]["state"] == "parcial"
    assert capabilities["axes"]["B"]["state"] == "parcial"
    assert "kaplan_meier" in capabilities["axes"]["B"]["pending"]
    assert all(capabilities["axes"][axis]["state"] == "planejado" for axis in "CD")
    assert capabilities["axes"]["E"]["state"] == "opcional_planejado"


@pytest.mark.requirement("REQ-MIG-009")
def test_spec_traceability(tmp_path):
    import shutil
    root = Path(__file__).resolve().parents[2] / "spec"
    module = importlib.util.spec_from_file_location("spec_check", root / "check.py"); checker = importlib.util.module_from_spec(module); module.loader.exec_module(checker)
    data = checker.validate(root)
    assert len(data["requirements"]) == 96
    assert all(r["state"] in ("planejado", "verificado") for r in data["requirements"])
    assert sum(1 for r in data["requirements"] if r["state"] == "verificado") == 43
    copy_root = tmp_path / "spec"; copy_root.mkdir()
    for name in ("requirements.json", "rastreabilidade.csv"): shutil.copyfile(root / name, copy_root / name)
    invalid = json.loads((copy_root / "requirements.json").read_bytes()); invalid["requirements"][0]["acceptance"] = ""
    (copy_root / "requirements.json").write_text(json.dumps(invalid), encoding="utf-8")
    with pytest.raises(ValueError, match="campo ausente"): checker.validate(copy_root)
    blocked = subprocess.run([sys.executable, str(root / "check.py"), "--release-all"], capture_output=True, text=True)
    assert blocked.returncode != 0 and "Release completo bloqueado" in blocked.stderr


@pytest.mark.requirement("REQ-MIG-006")
def test_streamlit_dashboard(monkeypatch, prepared):
    from streamlit.testing.v1 import AppTest
    from denguepharma_analytics import client as dashboard_client
    root, _ = prepared; api = TestClient(create_app(root))
    def get(path):
        response = api.get(path); response.raise_for_status(); return response.json()
    monkeypatch.setattr(dashboard_client, "get", get)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "src/denguepharma_analytics/dashboard.py"), default_timeout=30).run()
    assert not app.exception
    assert [(m.label, m.value) for m in app.metric] == [("Documentos coletados", "2"), ("Publicações", "1"), ("Registros de ensaios", "1"), ("Estudos revisados", "0")]
    assert any("panorama científico permanece vazio" in w.value for w in app.warning)
    assert [w.label for w in app.text_input] == ["E-mail", "Senha"]


@pytest.mark.requirement("REQ-MIG-007")
def test_quarto_report(prepared):
    from denguepharma_analytics.reports.render import render
    root, manifest = prepared
    executable = os.getenv("QUARTO_BIN")
    if not executable: pytest.skip("Configure QUARTO_BIN para renderizar com Quarto real")
    result = render(root, manifest["run_id"], executable)
    html = (root / "reports" / manifest["run_id"] / "report.html").read_text(encoding="utf-8")
    assert "Documentos: <strong>2</strong>" in html and "estudos revisados: <strong>0</strong>" in html and "Sem dados nesta camada" in html
    assert "2026-10-27" in html and "denominador" in html and "PRIVATE_FULLTEXT" not in html
    assert result["html_hash"] == digest((root / "reports" / manifest["run_id"] / "report.html").read_bytes())
    assert render(root, manifest["run_id"], executable) == result
    response = TestClient(create_app(root)).get(f'/api/public/analyses/{manifest["run_id"]}/artifacts?name=report.html')
    assert response.status_code == 200


def test_invalid_snapshot_rejected(snapshot):
    with pytest.raises(ValueError, match="HASH_MISMATCH"): load_snapshot(snapshot.content, expected_hash="a"*64)
    with pytest.raises(ValueError, match="DUPLICATE_JSON_KEY"): load_snapshot(b'{"x":1,"x":2}')
    data = copy.deepcopy(snapshot.data); data["scientificFields"] = [{"study_id": "s1", "published": False}]
    with pytest.raises(ValueError, match="ORPHAN"): load_snapshot(json.dumps(data).encode())
    data["studies"] = [{"studyId": "s1"}]
    with pytest.raises(ValueError, match="UNREVIEWED"): load_snapshot(json.dumps(data).encode())
