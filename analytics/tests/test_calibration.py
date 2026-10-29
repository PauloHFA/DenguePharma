import copy
import json
import os
from pathlib import Path
import shutil

import pytest
from fastapi.testclient import TestClient
from denguepharma_analytics.clinical.calibration import analyze,RULES
from denguepharma_analytics.clinical.screening_ui import payload,DEFAULTS
from denguepharma_analytics.preparation.documents import prepare
from denguepharma_analytics.domain import json_bytes
from denguepharma_analytics.sources.snapshot import load_snapshot


@pytest.mark.requirement("REQ-CLN-007")
def test_calibration_flags_are_document_counts_not_decisions(snapshot):
    data=copy.deepcopy(snapshot.data)
    for d in data["documents"][:2]:
        d["title"]="Dengue vaccine review with Aedes challenge"
        d["metadata"]["publication_types"]=["Review"]
    summary,tables=analyze(data,prepare(data)[0])
    assert summary["documents"]==2  # Two publications with the same PMID/DOI are one document.
    signals={r["code"]:r for r in summary["signals"]}
    assert signals["VACINA"]["count"]==1 and signals["REVISAO"]["count"]==1
    assert signals["DESAFIO_CONTROLADO"]["count"]==1 and signals["VETORES"]["count"]==1
    assert all(r["denominator"]==2 for r in signals.values())
    assert len(tables["calibration_documents"][0]["references"]) in {1,2}
    assert all(r["review_status"]=="SEM_REVISAO_CLINICA" for r in tables["calibration_documents"])
    assert not any("decision" in r for r in tables["calibration_documents"])
    assert snapshot.data["studies"]==[]


@pytest.mark.requirement("REQ-CLN-007")
def test_interventions_keep_the_declared_type_and_no_automatic_eligibility(snapshot):
    data=copy.deepcopy(snapshot.data)
    trial=data["documents"][-1]
    trial["title"]="Treatment trial"
    trial["metadata"]["protocolSection"]["armsInterventionsModule"]["interventions"]=[
        {"type":"BIOLOGICAL","name":"Investigational antibody"},{"type":"OTHER","name":"Wolbachia mosquitoes"},
        {"type":"DRUG","name":"Drug A"},{"type":"DRUG","name":"Drug A"}]
    data["sourceRuns"]=[dict(source="CLINICALTRIALS",total_returned=100,query="Dengue",params=dict(api_key="PRIVATE_KEY"))]
    summary,tables=analyze(data,prepare(data)[0])
    assert {r["intervention_type"]:r["count"] for r in summary["intervention_types"]}=={"BIOLOGICAL":1,"DRUG":1,"OTHER":1}
    row=next(r for r in tables["calibration_documents"] if r["document_type"]=="REGISTRO_ENSAIO")
    assert row["signal_codes"]==[]  # No inferred vaccine from BIOLOGICAL, or eligibility from DRUG.
    assert summary["searches"][0]["retrieved_fraction"]==.01
    assert "PRIVATE_KEY" not in json.dumps(summary)


@pytest.mark.requirement("REQ-CLN-007")
def test_empty_calibration_does_not_create_perfect_metrics():
    summary,tables=analyze(dict(documents=[],sourceRuns=[]),[])
    assert summary["documents"]==0 and summary["documents_with_signals"]==0
    assert len(summary["signals"])==len(RULES)
    assert all(r["proportion"] is None for r in tables["calibration_signals"])


@pytest.mark.requirement("REQ-CLN-007")
def test_calibration_export_public_report_and_older_run_compatibility(snapshot,tmp_path):
    from denguepharma_analytics.storage import export,publish,query_table
    from denguepharma_analytics.api import create_app
    from denguepharma_analytics.reports.render import render
    first=export(snapshot,tmp_path); publish(tmp_path,first["run_id"])
    app=TestClient(create_app(tmp_path)); base=f'/api/public/analyses/{first["run_id"]}'
    result=app.get(base+"/tables/calibration_documents").json()
    assert result["total"]==2
    report=app.get(base+"/artifacts",params={"name":"research_findings.md"})
    assert report.status_code==200 and "nenhum resultado clínico revisado" in report.text
    assert "PRIVATE_CONTACT" not in report.text and "PRIVATE_FULLTEXT" not in report.text and "PRIVATE_KEY" not in report.text
    public=app.get(base+"/tables/calibration_documents").text
    assert "PRIVATE_FULLTEXT" not in public and "PRIVATE_CONTACT" not in public
    assert export(snapshot,tmp_path)["run_id"]==first["run_id"]
    assert query_table(tmp_path,first["run_id"],"calibration_signals",source="PUBMED")["total"]==len(RULES)
    quarto=os.getenv("QUARTO_BIN") or shutil.which("quarto")
    if quarto:
        render(tmp_path,first["run_id"],quarto)
        html=(tmp_path/"reports"/first["run_id"]/"report.html").read_text(encoding="utf-8")
        assert "Sinais de metadados" in html and "{{CALIBRATION}}" not in html
    # Backward compatibility is tested against a historical snapshot when available locally.
    historical=Path(__file__).resolve().parents[1]/"data/runs/2665dc99d26e8a4b765664bed913e894b0fda613dd431ce2adbfd83eb90ad5d2"
    if historical.exists():
        old=TestClient(create_app(historical.parents[1])); old_base="/api/public/analyses/"+historical.name
        assert old.get(old_base+"/tables/corpus_documents").status_code==200
        assert old.get(old_base+"/tables/calibration_signals").status_code==404


@pytest.mark.requirement("REQ-CLN-001")
def test_screening_form_never_reuses_other_vote_or_infers_inclusion():
    row=dict(study_id="s1",basis_hash="a"*64,status="PENDENTE",own_decision=None,adjudication=None)
    data=payload(row,"INCERTO",dict(DEFAULTS,interventions=[]),"Reading permitted material remains pending")
    assert data["decision"]=="INCERTO" and data["classification"]["pharmacological_intervention"]=="INCERTO"
    with pytest.raises(ValueError): payload(row,"INCLUIR",dict(DEFAULTS,interventions=[]),"No unsupported inclusion allowed")
    with pytest.raises(ValueError): payload(row,"INCERTO",dict(DEFAULTS,interventions=[]),"Conflict adjudication unavailable",adjudicate=True)


@pytest.mark.requirement("REQ-CLN-001")
def test_structured_screening_form_submits_current_basis(monkeypatch):
    from streamlit.testing.v1 import AppTest
    from denguepharma_analytics import client
    row=dict(study_id="s1",basis_hash="a"*64,title="Synthetic study",status="PENDENTE",document_ids=["doc1"],own_decision=None,adjudication=None)
    calls=[]
    reads=[]
    def private(path,**kwargs):
        if "/dossier?" in path:
            reads.append(path)
            return dict(notice="Synthetic permitted documentary context",unresolved_identity_documents=[],documents=[])
        calls.append((path,kwargs))
        return {"event_id":"test-event"}
    monkeypatch.setattr(client,"private",private)
    script="from denguepharma_analytics.clinical.screening_ui import render\nrender("+repr(dict(queue=[row]))+",'workspace','private-token')"
    app=AppTest.from_string(script,default_timeout=30).run()
    assert not app.exception and not calls
    assert reads==["/workspace/studies/s1/dossier?basis_hash="+row["basis_hash"]]
    reason=next(w for w in app.text_area if w.label=="Justificativa e material consultado")
    reason.set_value("Human reviewer: insufficient permitted material")
    app.button[0].click().run()
    assert not app.exception and len(calls)==1
    assert calls[0][1]["data"]["basis_hash"]==row["basis_hash"] and calls[0][1]["data"]["decision"]=="INCERTO"
    assert "private-token" not in json.dumps(calls[0][1]["data"])
