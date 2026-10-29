"""Casos sinteticos identificados; nunca entram no corpus cientifico publicado."""
import copy
import json
import math
from pathlib import Path
from statistics import NormalDist

import pytest
from fastapi.testclient import TestClient
from denguepharma_analytics.clinical.effects import estimate
from denguepharma_analytics.clinical.models import Principal
from denguepharma_analytics.clinical.workspace import create
from denguepharma_analytics.domain import json_bytes
from denguepharma_analytics.sources.snapshot import load_snapshot

R1=Principal("reviewer-one",("PESQUISADOR",))
R2=Principal("reviewer-two",("PESQUISADOR",))
ADJ=Principal("adjudicator",("ADMINISTRADOR",))
CLASSIFICATION=dict(established_dengue="SIM",context="DOENCA_ESTABELECIDA",population="ADULTOS",severity="NAO_GRAVE",disease_phase="FEBRIL",purpose="TRATAMENTO",design="RCT_PARALELO",interventions=["TEST-DRUG"],pharmacological_intervention="SIM")


@pytest.fixture
def workspace(tmp_path,snapshot):
    data=copy.deepcopy(snapshot.data)
    # O texto sintetico contem os valores apenas para testar suporte literal.
    for document in data["documents"]:
        document["metadata"]["abstract"]="TEST-DRUG versus PLACEBO in adults at day 7; 10 of 100 versus 5 of 100. Methodological assessment available."
    protocol=json.loads((Path(__file__).resolve().parents[2]/"spec/clinical/protocolo.json").read_bytes())
    return create(tmp_path,load_snapshot(json_bytes(data)),protocol)


def screen(workspace,actor=R1,study="s1",decision="INCLUIR",classification=None):
    row=next(r for r in workspace.queue(actor) if r["study_id"]==study)
    return workspace.act("SCREENED",dict(study_id=study,basis_hash=row["basis_hash"],decision=decision,classification=classification or CLASSIFICATION,reason="Reviewed source manually for test"),actor)


def include(workspace):
    screen(workspace); screen(workspace,R2)


def result(workspace):
    state=workspace.private_state(R1)
    row=next(r for r in state["queue"] if r["study_id"]=="s1")
    version=next(s for s in state["sources"] if s["document_id"]=="p1")
    source=workspace.source(version["version_id"],R1)
    fields=["intervention","comparator","population","outcome_definition","timepoint","risk_of_bias","treatment.n","treatment.events","control.n","control.events"]
    evidence=[dict(field=f,version_id=source["version_id"],text_hash=source["text_hash"],start=0,end=len(source["text"]),quote=source["text"]) for f in fields]
    return dict(study_id="s1",basis_hash=row["basis_hash"],comparison_id="arm-a-vs-b",intervention="TEST-DRUG",comparator="PLACEBO",population="ADULTOS",severity="NAO_GRAVE",disease_phase="FEBRIL",intervention_timing="within 72h",analysis_population="ITT",purpose="TRATAMENTO",design="RCT_PARALELO",outcome_code="EVENTOS_ADVERSOS",outcome_definition="Any adverse event",timepoint="day 7",unit="participants",direction="MENOR_MELHOR",effect_type="RR",treatment=dict(arm_id="a",n=100,events=10),control=dict(arm_id="b",n=100,events=5),independent_arms=True,support_care="Hydration according to protocol",limitations="Synthetic test data only",risk_of_bias="NAO_AVALIADO",risk_of_bias_reason="Assessment pending in fixture",evidence=evidence)


def selection_hash(workspace):
    with workspace.transaction() as db: return workspace.selection_hash(db,workspace.events(db))


def complete_calibration(workspace):
    screen(workspace,R1,"s2",decision="EXCLUIR"); screen(workspace,R2,"s2",decision="EXCLUIR")
    workspace.act("CALIBRATION_APPROVED",dict(selection_hash=selection_hash(workspace),sentinel_ids=["s1"],reason="Synthetic reviewed calibration with complete selection"),ADJ)


def approve(workspace,payload):
    candidate=workspace.act("RESULT_DRAFTED",payload,R1)["event_id"]
    workspace.act("RESULT_REVIEWED",dict(result_id=candidate,decision="ACEITAR",reason="Values checked independently"),R2)
    workspace.act("RESULT_ADJUDICATED",dict(result_id=candidate,decision="ACEITAR",reason="Resolved by independent adjudicator"),ADJ)
    return candidate


@pytest.mark.requirement("REQ-CLN-002")
def test_effects_known_values():
    binary=dict(effect_type="RR",design="RCT_PARALELO",independent_arms=True,treatment=dict(arm_id="a",n=100,events=10),control=dict(arm_id="b",n=100,events=5))
    effect=estimate(binary)
    margin=NormalDist().inv_cdf(.975)*math.sqrt(1/10-1/100+1/5-1/100)
    assert effect["estimate"]==2
    assert effect["ci_low"]==pytest.approx(math.exp(math.log(2)-margin))
    assert effect["ci_high"]==pytest.approx(math.exp(math.log(2)+margin))
    binary["treatment"]["events"]=0
    assert estimate(binary)["estimate"] is None
    binary["treatment"]["events"]=101
    with pytest.raises(ValueError): estimate(binary)
    continuous=dict(effect_type="MD",design="RCT_PARALELO",independent_arms=True,treatment=dict(arm_id="a",n=10,mean=3.,sd=2.),control=dict(arm_id="b",n=10,mean=5.,sd=2.))
    effect=estimate(continuous)
    assert effect["estimate"]==-2
    assert effect["ci_low"]==pytest.approx(-3.879121798,rel=1e-6)
    continuous["treatment"]["mean"]=None
    with pytest.raises(ValueError): estimate(continuous)
    reported=dict(effect_type="REPORTED",reported=dict(measure="HR",estimate=.8,ci_low=.4,ci_high=1.4,confidence_level=.95))
    assert estimate(reported)["estimate"]==.8
    reported["reported"]["ci_low"]=.9
    with pytest.raises(ValueError): estimate(reported)


@pytest.mark.requirement("REQ-CLN-001")
def test_independent_screening_and_stale_sources(workspace):
    screen(workspace)
    state=workspace.queue(R2)[0]
    assert state["own_decision"] is None and state["classification"] is None and state["adjudication"] is None
    screen(workspace,R2,decision="EXCLUIR")
    row=workspace.queue(ADJ)[0]
    assert row["status"]=="CONFLITO"
    payload=dict(study_id="s1",basis_hash=row["basis_hash"],votes_hash=row["adjudication"]["votes_hash"],decision="INCLUIR",classification=CLASSIFICATION,reason="Conflict independently adjudicated")
    with pytest.raises(PermissionError): workspace.act("SCREEN_ADJUDICATED",payload,Principal(R1.id,("ADMINISTRADOR",)))
    workspace.act("SCREEN_ADJUDICATED",payload,ADJ)
    assert workspace.queue(R1)[0]["status"]=="INCLUIR"
    workspace.attach_source(workspace.input.data["documents"][0],"Updated normalized source")
    assert workspace.queue(R1)[0]["status"]=="PENDENTE"
    with pytest.raises(ValueError,match="STALE"): workspace.act("SCREENED",{k:v for k,v in payload.items() if k!="votes_hash"},R1)
    wrong=dict(CLASSIFICATION,context="PROFILAXIA")
    with pytest.raises(ValueError): screen(workspace,classification=wrong)


@pytest.mark.requirement("REQ-CLN-003")
def test_result_review_provenance_deduplication_and_corrections(workspace):
    include(workspace); payload=result(workspace)
    draft=workspace.act("RESULT_DRAFTED",payload,R1)["event_id"]
    with pytest.raises(PermissionError): workspace.act("RESULT_REVIEWED",dict(result_id=draft,decision="ACEITAR",reason="Self review forbidden"),R1)
    with pytest.raises(ValueError,match="INDEPENDENT_REVIEW"): workspace.act("RESULT_ADJUDICATED",dict(result_id=draft,decision="ACEITAR",reason="No independent review yet"),ADJ)
    first=approve(workspace,payload); second=approve(workspace,payload)
    frozen=workspace.freeze()
    assert len(frozen["results"])==1 and len(frozen["results"][0]["document_result_ids"])==2
    assert frozen["groups"][0]["study_count"]==1
    assert "reviewer-one" not in json.dumps(frozen) and '"quote"' not in json.dumps(frozen)
    correction=dict(payload,supersedes=first,correction_reason="Corrected extraction pending approval")
    workspace.act("RESULT_DRAFTED",correction,R1)
    assert len(workspace.freeze()["results"][0]["document_result_ids"])==2
    # A divergent approved extraction blocks the comparison instead of selecting the latest.
    divergent=copy.deepcopy(payload); divergent["control"]["events"]=10
    approve(workspace,divergent)
    assert workspace.freeze()["results"]==[] and len(workspace.freeze()["conflicts"])==1


@pytest.mark.requirement("REQ-CLN-003")
def test_literal_evidence_is_required(workspace):
    include(workspace); payload=result(workspace); payload["evidence"][0]["quote"]="Invented support"
    candidate=workspace.act("RESULT_DRAFTED",payload,R1)["event_id"]
    workspace.act("RESULT_REVIEWED",dict(result_id=candidate,decision="ACEITAR",reason="Independent review submitted"),R2)
    with pytest.raises(ValueError,match="LITERAL"): workspace.act("RESULT_ADJUDICATED",dict(result_id=candidate,decision="ACEITAR",reason="Cannot approve invented text"),ADJ)
    assert workspace.freeze()["results"]==[]


@pytest.mark.requirement("REQ-CLN-004")
def test_human_conclusion_and_invalidation(workspace):
    include(workspace); payload=result(workspace); approve(workspace,payload)
    complete_calibration(workspace)
    group=workspace.freeze()["groups"][0]
    assert group["category"]=="REVISAO_DA_SINTESE_PENDENTE"
    conclusion=dict(selection_hash=selection_hash(workspace),scope=group["scope"],result_set_hash=group["result_set_hash"],category="EVIDENCIA_INCONCLUSIVA",rationale="Synthetic evidence insufficient",clinical_importance="No clinical conclusion from fixtures",uncertainty="Small sample and wide interval",consistency="Only one synthetic trial available",limitations="No independent methodological assessment")
    with pytest.raises(ValueError,match="RANDOMIZED"): workspace.act("SYNTHESIS_CONCLUDED",dict(conclusion,category="BENEFICIO_SUSTENTADO"),ADJ)
    workspace.act("SYNTHESIS_CONCLUDED",conclusion,ADJ)
    assert workspace.freeze()["groups"][0]["category"]=="EVIDENCIA_INCONCLUSIVA"
    approve(workspace,payload)
    # Duplicate evidence does not add a study; changed decision set still requires renewed judgment.
    assert workspace.freeze()["groups"][0]["study_count"]==1
    assert workspace.freeze()["groups"][0]["category"]=="REVISAO_DA_SINTESE_PENDENTE"
    # Selection changes invalidate all reviewed results.
    screen(workspace,R1,decision="EXCLUIR")
    assert workspace.freeze()["results"]==[]


@pytest.mark.requirement("REQ-CLN-004")
def test_no_automatic_absence(workspace):
    assert workspace.freeze()["absences"]==[]
    with pytest.raises(ValueError,match="SCREENING_NOT_COMPLETE"): workspace.act("ABSENCE_CONCLUDED",dict(selection_hash=selection_hash(workspace),intervention="TEST-DRUG",population="ADULTOS",reason="No eligible trial found in reviewed corpus"),ADJ)
    for study in ("s1","s2"):
        screen(workspace,R1,study,decision="EXCLUIR"); screen(workspace,R2,study,decision="EXCLUIR")
    workspace.act("CALIBRATION_APPROVED",dict(selection_hash=selection_hash(workspace),sentinel_ids=["s1"],reason="Synthetic calibration reviewed completely"),ADJ)
    workspace.act("ABSENCE_CONCLUDED",dict(selection_hash=selection_hash(workspace),intervention="TEST-DRUG",population="ADULTOS",reason="No eligible trial found in reviewed corpus"),ADJ)
    assert len(workspace.freeze()["absences"])==1
    screen(workspace,R1,decision="INCLUIR")
    assert workspace.freeze()["absences"]==[]


@pytest.mark.requirement("REQ-CLN-005")
def test_clinical_export_api_and_permissions(workspace,tmp_path):
    from denguepharma_analytics.storage import export,publish
    from denguepharma_analytics.api import create_app
    include(workspace); approve(workspace,result(workspace))
    snapshot=workspace.snapshot(); manifest=export(snapshot,tmp_path)
    assert export(snapshot,tmp_path)["run_id"]==manifest["run_id"]
    publish(tmp_path,manifest["run_id"])
    def auth(token): return {"researcher":R1,"reader":Principal("reader",("LEITOR",))}[token]
    app=TestClient(create_app(tmp_path,authenticate=auth)); prefix=f"/api/clinical/{workspace.key}"
    assert app.get(prefix+"/state").status_code==401
    assert app.get(prefix+"/state",headers={"Authorization":"Bearer reader"}).status_code==403
    state=app.get(prefix+"/state",headers={"Authorization":"Bearer researcher"})
    assert state.status_code==200 and len(state.json()["approved_results"])==1
    base=f'/api/public/analyses/{manifest["run_id"]}'
    response=app.get(base+"/tables/clinical_results")
    assert response.status_code==200 and response.json()["total"]==1
    assert response.json()["rows"][0]["participants_comparison"]==200
    assert app.get(base+"/artifacts",params={"name":"clinical_results.csv"}).status_code==200
    assert app.get(base+"/artifacts",params={"name":"clinical/curation.sqlite3"}).status_code==404
    assert any(name.startswith("figures/") for name in manifest["artifacts"])
    figure=next(name for name in manifest["artifacts"] if name.startswith("figures/"))
    assert app.get(base+"/artifacts",params={"name":figure}).content[:8]==b"\x89PNG\r\n\x1a\n"
    public=app.get(base+"/summary").json()["clinical"]
    assert public["reviewed_studies"]==1 and public["reviewed_results"]==1


@pytest.mark.requirement("REQ-CLN-005")
def test_clinical_cli_equivalence_and_report(workspace,tmp_path):
    import os,subprocess,sys,shutil
    from denguepharma_analytics.storage import export
    from denguepharma_analytics.reports.render import render
    include(workspace); approve(workspace,result(workspace))
    expected=export(workspace.snapshot(),tmp_path)
    completed=subprocess.run([sys.executable,"-m","denguepharma_analytics.cli","--data-dir",str(tmp_path),"clinical-freeze","--workspace",workspace.key],capture_output=True,text=True,timeout=45)
    assert completed.returncode==0,completed.stderr
    assert json.loads(completed.stdout)["run_id"]==expected["run_id"]
    executable=os.getenv("QUARTO_BIN") or shutil.which("quarto")
    if executable:
        report=render(tmp_path,expected["run_id"],executable)
        content=(tmp_path/"reports"/expected["run_id"]/"report.html").read_text(encoding="utf-8")
        assert "data:image/png;base64," in content and "TEST-DRUG" in content
        assert "reviewer-one" not in content
        assert report["input_hash"]==expected["input_hash"]


@pytest.mark.requirement("REQ-CLN-001","REQ-CLN-004")
def test_observational_and_mixed_populations(workspace):
    classification=dict(CLASSIFICATION,population="MISTA_SEM_SEPARACAO",design="OBSERVACIONAL")
    screen(workspace,R1,classification=classification); screen(workspace,R2,classification=classification)
    # A fresh source invalidates prior screening, requiring renewed independent decisions.
    document=workspace.input.data["documents"][0]
    workspace.attach_source(document,"TEST-DRUG vs PLACEBO; pediatric results: RR 2, CI 1.1 to 4; day 7. Methodological assessment.")
    screen(workspace,R1,classification=classification); screen(workspace,R2,classification=classification)
    payload=result(workspace); payload.update(design="OBSERVACIONAL",population="PEDIATRICO",effect_type="REPORTED",reported=dict(measure="RR",estimate=2.,ci_low=1.1,ci_high=4.,confidence_level=.95))
    state=workspace.private_state(R1); version=next(v for v in state["sources"] if ":" in v["version_id"])
    source=workspace.source(version["version_id"],R1)
    payload["evidence"]=[dict(field=f,version_id=source["version_id"],text_hash=source["text_hash"],start=0,end=len(source["text"]),quote=source["text"]) for f in ("intervention","comparator","population","outcome_definition","timepoint","risk_of_bias","reported.estimate","reported.ci_low","reported.ci_high")]
    approve(workspace,payload)
    complete_calibration(workspace)
    group=workspace.freeze()["groups"][0]
    assert group["scope"]["design_layer"]=="OBSERVACIONAL" and group["scope"]["population"]=="PEDIATRICO"
    conclusion=dict(selection_hash=selection_hash(workspace),scope=group["scope"],result_set_hash=group["result_set_hash"],category="BENEFICIO_SUSTENTADO",rationale="Cannot establish benefit from this layer",clinical_importance="No supported clinical conclusion",uncertainty="Confounding remains possible",consistency="Single observational study",limitations="Synthetic test data only")
    with pytest.raises(ValueError,match="RANDOMIZED"): workspace.act("SYNTHESIS_CONCLUDED",conclusion,ADJ)


@pytest.mark.requirement("REQ-CLN-005")
def test_collection_checkpoint_uses_clinical_query(tmp_path):
    from denguepharma_analytics.clinical.collection import collect
    from denguepharma_analytics.domain import digest
    protocol=json.loads((Path(__file__).resolve().parents[2]/"spec/clinical/protocolo.json").read_bytes())
    class Client:
        def __init__(self): self.writes=[]
        def login(self): pass
        def call(self,path,body=None,binary=False):
            if body is not None: self.writes.append((path,body))
            if path=="/api/protocols":
                assert body["strategy"]["maxRecords"]==10 and body["strategy"]["pubmed"]["query"]==protocol["search"]["pubmed"]
                return {"id":"protocol-1"}
            if path=="/api/imports": return {"runId":"import-"+body["source"]}
            if path=="/api/analyses/corpus": return {"id":"analysis-1"}
            if binary: return b'{"documents":[]}'
            return {"status":"COMPLETED"}
    client=Client(); first=collect(protocol,"2026-01-01",tmp_path,client)
    before=len(client.writes); second=collect(protocol,"2026-01-01",tmp_path,client)
    assert first==second and len(client.writes)==before
    assert first["input_hash"]==digest((tmp_path/"dataset.json").read_bytes())
    with pytest.raises(ValueError,match="CONFIGURATION"): collect(protocol,"2026-01-02",tmp_path,client)
