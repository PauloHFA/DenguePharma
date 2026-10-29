import copy
import pytest
from fastapi.testclient import TestClient

from test_clinical import workspace,R1,R2,ADJ,CLASSIFICATION,include,result,approve,screen
from denguepharma_analytics.api import create_app
from denguepharma_analytics.clinical.extraction import preview,workflow
from denguepharma_analytics.clinical.extraction_ui import numeric,build_payload,occurrences
from denguepharma_analytics.clinical.models import Principal


def event_count(workspace):
    with workspace.transaction() as db: return len(workspace.events(db))


@pytest.mark.requirement("REQ-CLN-009")
def test_extraction_parsing_preserves_missing_zero_and_decimal_values(workspace):
    assert numeric("") is None and numeric("0",integer=True)==0
    assert numeric("0,95")==.95 and numeric("-1.5")==-1.5
    for text in ("nan","Infinity","1,234.5"):
        with pytest.raises(ValueError): numeric(text)
    with pytest.raises(ValueError): numeric("100,0",integer=True)
    assert occurrences("á😀 xx xx","xx")==[3,6]
    assert occurrences("aaaa","aa")==[0,1,2]
    data=result_after_include(workspace)
    data["treatment"]["n"]="100"; data["treatment"]["events"]="0"
    converted=build_payload(data,"domain1=Methods reviewed")
    assert converted["treatment"]["events"]==0 and converted["treatment"]["n"]==100
    assert data["treatment"]["n"]=="100"  # No mutation of the input form.
    with pytest.raises(ValueError,match="repetido"): build_payload(data,"d=one\nd=two")


def result_after_include(workspace):
    include(workspace); return result(workspace)


@pytest.mark.requirement("REQ-CLN-009")
def test_preview_uses_same_validation_without_events_or_publication(workspace):
    payload=result_after_include(workspace); before=event_count(workspace)
    value=preview(workspace,payload,R1)
    assert value["effect"]["estimate"]==2 and value["support"]["complete"] is True and not value["published"]
    assert event_count(workspace)==before and workspace.freeze()["results"]==[]
    payload["evidence"]=[]
    assert preview(workspace,payload,R1)["support"]["complete"] is False
    invalid=copy.deepcopy(payload);invalid["treatment"]["events"]=101
    with pytest.raises(ValueError,match="EXCEED"): preview(workspace,invalid,R1)
    with pytest.raises(ValueError,match="EXCEED"): workspace.act("RESULT_DRAFTED",invalid,R1)
    assert event_count(workspace)==before


@pytest.mark.requirement("REQ-CLN-009")
def test_extraction_workflow_independence_and_approval_states(workspace):
    payload=result_after_include(workspace)
    candidate=workspace.act("RESULT_DRAFTED",payload,R1)["event_id"]
    author=workflow(workspace,R1)["candidates"][0]
    assert author["stage"]=="AGUARDA_REVISAO" and not author["can_review"] and not author["can_adjudicate"]
    assert workflow(workspace,R2)["candidates"][0]["can_review"]
    workspace.act("RESULT_REVIEWED",dict(result_id=candidate,decision="ACEITAR",reason="Values independently checked"),R2)
    third=workflow(workspace,ADJ)["candidates"][0]
    assert third["stage"]=="AGUARDA_ADJUDICACAO" and third["can_adjudicate"]
    assert not workflow(workspace,R2)["candidates"][0]["can_adjudicate"]
    workspace.act("RESULT_ADJUDICATED",dict(result_id=candidate,decision="ACEITAR",reason="Sources independently adjudicated"),ADJ)
    assert workflow(workspace,ADJ)["candidates"][0]["stage"]=="APROVADO"
    assert len(workspace.freeze()["results"])==1


@pytest.mark.requirement("REQ-CLN-009")
def test_updated_selection_classification_invalidates_old_results(workspace):
    payload=result_after_include(workspace); approve(workspace,payload)
    updated=dict(CLASSIFICATION,interventions=["DIFFERENT-DRUG"])
    screen(workspace,R1,classification=updated);screen(workspace,R2,classification=updated)
    flow=workflow(workspace,R2)
    assert flow["included_studies"] and flow["candidates"][0]["stage"]=="BASE_DESATUALIZADA"
    assert not flow["candidates"][0]["can_review"] and workspace.freeze()["results"]==[]
    with pytest.raises(ValueError,match="INTERVENTION_NOT_SCREENED"): preview(workspace,payload,R1)
    candidate=flow["candidates"][0]["id"]
    with pytest.raises(ValueError,match="INTERVENTION_NOT_SCREENED"):
        workspace.act("RESULT_REVIEWED",dict(result_id=candidate,decision="ACEITAR",reason="Old classification cannot be reused"),R2)


@pytest.mark.requirement("REQ-CLN-009")
def test_extraction_endpoints_are_private_and_pending_studies_are_blocked(workspace,tmp_path):
    actors={"one":R1,"reader":Principal("reader",("LEITOR",))}
    app=TestClient(create_app(tmp_path,authenticate=lambda token:actors[token])); prefix=f"/api/clinical/{workspace.key}"
    assert app.get(prefix+"/extraction").status_code==401
    assert app.get(prefix+"/extraction",headers={"Authorization":"Bearer reader"}).status_code==403
    headers={"Authorization":"Bearer one"}
    assert app.get(prefix+"/extraction",headers=headers).json()["included_studies"]==[]
    include(workspace); payload=result(workspace)
    assert app.post(prefix+"/results/preview",json=payload).status_code==401
    response=app.post(prefix+"/results/preview",headers=headers,json=payload)
    assert response.status_code==200 and response.json()["effect"]["estimate"]==2
    assert app.post(prefix+"/results/preview",headers=headers,json=dict(payload,actor="forged")).status_code==422
    assert event_count(workspace)==2
    screen(workspace,R1,decision="EXCLUIR")
    assert app.post(prefix+"/results/preview",headers=headers,json=payload).status_code==409


@pytest.mark.requirement("REQ-CLN-009")
def test_extraction_form_shows_pending_block_without_save_controls(monkeypatch):
    from streamlit.testing.v1 import AppTest
    from denguepharma_analytics import client
    calls=[]
    flow=dict(included_studies=[],candidates=[],outcomes={},conflicts=[])
    monkeypatch.setattr(client,"private",lambda path,**kwargs:calls.append(path) or flow)
    app=AppTest.from_string("from denguepharma_analytics.clinical.extraction_ui import render\nrender({'sources':[]},'workspace','token')",default_timeout=30).run()
    assert not app.exception and any("Extração bloqueada" in i.value for i in app.info)
    assert not app.button and calls==["/workspace/extraction"]


@pytest.mark.requirement("REQ-CLN-009")
def test_field_form_previews_and_saves_only_a_draft(workspace,monkeypatch):
    from streamlit.testing.v1 import AppTest
    from denguepharma_analytics import client
    include(workspace); state=workspace.private_state(R1); calls=[]
    def private(path,**kwargs):
        calls.append(path)
        if path.endswith("/extraction"): return workflow(workspace,R1)
        if path.endswith("/results/preview"): return preview(workspace,kwargs["data"],R1)
        if path.endswith("/actions/RESULT_DRAFTED"): return workspace.act("RESULT_DRAFTED",kwargs["data"],R1)
        raise AssertionError(path)
    monkeypatch.setattr(client,"private",private)
    script="from denguepharma_analytics.clinical.extraction_ui import render\nrender("+repr(dict(sources=state["sources"]))+",'workspace','token')"
    app=AppTest.from_string(script,default_timeout=30).run()
    assert not app.exception
    values={"Identificador estável da comparação":"a-vs-b","Comparador":"PLACEBO","Momento de início da intervenção":"within 72h","População de análise (ITT, PP ou outra)":"ITT","Definição do desfecho":"Any adverse event","Período de avaliação":"day 7","Unidade do resultado":"participants","Identificador do braço — Intervenção":"a","Identificador do braço — Comparador":"b","Estimativa publicada":"0,8","Limite inferior do intervalo":"0,4","Limite superior do intervalo":"1,4","Nível de confiança (ex.: 0,95)":"0,95"}
    for widget in app.text_input:
        if widget.label in values: widget.set_value(values[widget.label])
    for widget in app.text_area:
        if widget.label in {"Cuidados de suporte e cointervenções","Limitações e informações não disponíveis","Justificativa da avaliação metodológica"}:widget.set_value("Synthetic test information only")
    next(w for w in app.text_input if w.label=="Estimativa publicada").set_value("NaN")
    next(b for b in app.button if b.label=="Conferir rascunho sem salvar").click().run()
    assert not app.exception and app.error and event_count(workspace)==2
    assert not any(p.endswith("/results/preview") for p in calls)
    next(w for w in app.text_input if w.label=="Estimativa publicada").set_value("0,8")
    next(b for b in app.button if b.label=="Conferir rascunho sem salvar").click().run()
    assert not app.exception and not app.error and event_count(workspace)==2
    assert any(p.endswith("/results/preview") for p in calls)
    next(b for b in app.button if b.label=="Salvar rascunho para revisão independente").click().run()
    assert not app.exception and not app.error and event_count(workspace)==3
    assert workspace.freeze()["results"]==[]


@pytest.mark.requirement("REQ-CLN-009")
def test_review_and_adjudication_forms_require_explicit_decisions(workspace,monkeypatch):
    from streamlit.testing.v1 import AppTest
    from denguepharma_analytics import client
    from denguepharma_analytics.clinical.extraction_ui import decisions
    payload=result_after_include(workspace)
    workspace.act("RESULT_DRAFTED",payload,R1)
    def run(actor,action,label):
        flow=workflow(workspace,actor); calls=[]
        def private(path,**kwargs):
            calls.append(path);return workspace.act(action,kwargs["data"],actor)
        monkeypatch.setattr(client,"private",private)
        app=AppTest.from_string("from denguepharma_analytics.clinical.extraction_ui import decisions\ndecisions("+repr(flow)+",'workspace','token')",default_timeout=30).run()
        assert not app.exception and not calls
        button=next(b for b in app.button if b.label=="Registrar "+label.lower())
        assert not button.disabled
        next(w for w in app.selectbox if w.label==label).select("ACEITAR")
        next(w for w in app.text_area if w.label=="Justificativa — "+label).set_value("Synthetic independent verification against source")
        button.click().run()
        assert not app.exception and not app.error and len(calls)==1
    run(R2,"RESULT_REVIEWED","Revisão independente")
    assert workspace.freeze()["results"]==[]
    run(ADJ,"RESULT_ADJUDICATED","Adjudicação")
    assert len(workspace.freeze()["results"])==1
