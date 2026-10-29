import copy
import pytest
from fastapi.testclient import TestClient
from test_clinical import workspace,R1,R2,ADJ,CLASSIFICATION,include,result,approve,screen,selection_hash,complete_calibration
from denguepharma_analytics.api import create_app
from denguepharma_analytics.clinical.models import Principal
from denguepharma_analytics.clinical.synthesis import view


def conclusion(workspace,category="EVIDENCIA_INCONCLUSIVA"):
    group=workspace.freeze()["groups"][0]
    return dict(selection_hash=selection_hash(workspace),scope=group["scope"],result_set_hash=group["result_set_hash"],category=category,
        rationale="Synthetic evidence is insufficient",clinical_importance="Clinical importance reviewed independently",uncertainty="Wide intervals and uncertainty documented",consistency="Only one synthetic study available",limitations="Synthetic fixture without complete bias assessment")


def prepared(workspace):
    include(workspace);approve(workspace,result(workspace));complete_calibration(workspace)


@pytest.mark.requirement("REQ-CLN-010")
def test_synthesis_requires_complete_selection_and_calibration_in_api(workspace):
    include(workspace);approve(workspace,result(workspace))
    with pytest.raises(ValueError,match="SCREENING_NOT_COMPLETE"):workspace.act("SYNTHESIS_CONCLUDED",conclusion(workspace),ADJ)
    for actor in (R1,R2):screen(workspace,actor,"s2",decision="EXCLUIR")
    with pytest.raises(ValueError,match="CALIBRATION_NOT_APPROVED"):workspace.act("SYNTHESIS_CONCLUDED",conclusion(workspace),ADJ)
    workspace.act("CALIBRATION_APPROVED",dict(selection_hash=selection_hash(workspace),sentinel_ids=["s1"],reason="Reviewed calibration with all selections resolved"),ADJ)
    assert view(workspace,ADJ)["groups"][0]["can_conclude"]
    workspace.act("SYNTHESIS_CONCLUDED",conclusion(workspace),ADJ)
    assert workspace.freeze()["groups"][0]["category"]=="EVIDENCIA_INCONCLUSIVA"


@pytest.mark.requirement("REQ-CLN-010")
def test_changed_selection_invalidates_calibration_and_judgment(workspace):
    prepared(workspace);old=conclusion(workspace)
    workspace.act("SYNTHESIS_CONCLUDED",old,ADJ)
    # Even an updated screening justification is a new decision set, requiring renewed approval.
    screen(workspace,R1)
    current=view(workspace,ADJ)
    assert current["selection_complete"] and not current["calibration_approved"]
    assert current["groups"][0]["category"]=="REVISAO_DA_SINTESE_PENDENTE"
    with pytest.raises(ValueError,match="STALE_SELECTION"):workspace.act("SYNTHESIS_CONCLUDED",old,ADJ)
    with pytest.raises(ValueError,match="STALE_SELECTION"):
        workspace.act("CALIBRATION_APPROVED",dict(selection_hash=old["selection_hash"],sentinel_ids=["s1"],reason="Old form cannot approve a new selection"),ADJ)


@pytest.mark.requirement("REQ-CLN-010")
def test_synthesis_blocks_roles_conflicts_and_unsupported_benefit(workspace):
    prepared(workspace)
    observer=view(workspace,R1)
    assert not observer["groups"][0]["can_conclude"]
    assert "BENEFICIO_SUSTENTADO" not in observer["groups"][0]["available_categories"]
    with pytest.raises(PermissionError):workspace.act("SYNTHESIS_CONCLUDED",conclusion(workspace),R1)
    with pytest.raises(ValueError,match="RANDOMIZED"):workspace.act("SYNTHESIS_CONCLUDED",conclusion(workspace,"BENEFICIO_SUSTENTADO"),ADJ)
    old=conclusion(workspace);draft=copy.deepcopy(result(workspace));draft["control"]["events"]=10
    approve(workspace,draft)
    assert view(workspace,ADJ)["conflicts"]
    with pytest.raises(ValueError,match="CONFLICTS"):workspace.act("SYNTHESIS_CONCLUDED",old,ADJ)


@pytest.mark.requirement("REQ-CLN-010")
def test_mixed_population_prevents_false_absence(workspace):
    mixed=dict(CLASSIFICATION,population="MISTA_SEM_SEPARACAO")
    screen(workspace,R1,classification=mixed);screen(workspace,R2,classification=mixed)
    complete_calibration(workspace)
    for population in ("ADULTOS","PEDIATRICO","MISTA_SEM_SEPARACAO"):
        payload=dict(selection_hash=selection_hash(workspace),intervention="TEST-DRUG",population=population,reason="No extracted result is not absence of eligible study")
        with pytest.raises(ValueError,match="ELIGIBLE_STUDY_EXISTS"):workspace.act("ABSENCE_CONCLUDED",payload,ADJ)
    workspace.act("ABSENCE_CONCLUDED",dict(selection_hash=selection_hash(workspace),intervention="UNSTUDIED-TEST-DRUG",population="ADULTOS",reason="Synthetic scoped absence after complete human selection"),ADJ)
    assert len(workspace.freeze()["absences"])==1


@pytest.mark.requirement("REQ-CLN-010")
def test_calibration_rejects_duplicate_sentinels_and_missing_hash(workspace):
    include(workspace)
    for actor in (R1,R2):screen(workspace,actor,"s2",decision="EXCLUIR")
    data=dict(selection_hash=selection_hash(workspace),sentinel_ids=["s1","s1"],reason="Duplicated sentinel must not masquerade as coverage")
    with pytest.raises(ValueError,match="DUPLICATE_SENTINELS"):workspace.act("CALIBRATION_APPROVED",data,ADJ)
    with pytest.raises(ValueError):workspace.act("CALIBRATION_APPROVED",{k:v for k,v in data.items() if k!="selection_hash"},ADJ)
    assert not view(workspace,ADJ)["calibration_approved"]
    from denguepharma_analytics.clinical.workspace import create
    from denguepharma_analytics.sources.snapshot import load_snapshot
    from denguepharma_analytics.domain import json_bytes
    empty_data=copy.deepcopy(workspace.input.data);empty_data["documents"]=[]
    empty=create(workspace.root/"empty",load_snapshot(json_bytes(empty_data)),workspace.protocol)
    assert not view(empty,ADJ)["selection_complete"] and not view(empty,ADJ)["can_approve_calibration"]
    with pytest.raises(ValueError,match="EMPTY_CORPUS"):
        empty.act("CALIBRATION_APPROVED",dict(selection_hash=selection_hash(empty),sentinel_ids=["missing"],reason="Empty corpus cannot establish a reviewed calibration"),ADJ)


@pytest.mark.requirement("REQ-CLN-010")
def test_synthesis_state_is_private_and_empty_groups_are_not_inconclusive(workspace,tmp_path):
    client=TestClient(create_app(tmp_path,authenticate=lambda token:{"one":R1,"reader":Principal("reader",("LEITOR",))}[token]))
    url=f"/api/clinical/{workspace.key}/synthesis"
    assert client.get(url).status_code==401
    assert client.get(url,headers={"Authorization":"Bearer reader"}).status_code==403
    state=client.get(url,headers={"Authorization":"Bearer one"}).json()
    assert state["groups"]==[] and not state["can_conclude_absence"] and not state["calibration_approved"]
    assert "SELECAO_INDEPENDENTE_PENDENTE" in state["blockers"]


@pytest.mark.requirement("REQ-CLN-010")
def test_calibration_and_conclusion_forms_submit_explicit_human_decisions(workspace,monkeypatch):
    from streamlit.testing.v1 import AppTest
    from denguepharma_analytics import client
    include(workspace);approve(workspace,result(workspace))
    for actor in (R1,R2):screen(workspace,actor,"s2",decision="EXCLUIR")
    calls=[]
    def private(path,**kwargs):
        if path.endswith("/synthesis"):return view(workspace,ADJ)
        calls.append((path,kwargs["data"]));return workspace.act(path.rsplit("/",1)[-1],kwargs["data"],ADJ)
    monkeypatch.setattr(client,"private",private)
    script="from denguepharma_analytics.clinical.synthesis_ui import render\nrender('workspace','token')"
    app=AppTest.from_string(script,default_timeout=30).run()
    assert not app.exception and not calls
    app.multiselect[0].select("s1")
    next(w for w in app.text_area if w.label=="Achados da calibração, limitações da busca e ajustes necessários").set_value("Synthetic sentinel sensitivity checked with limitations documented")
    next(w for w in app.checkbox if w.label.startswith("Conferi as referências")).check()
    next(b for b in app.button if b.label=="Registrar aprovação da calibração").click().run()
    assert not app.exception and not app.error and calls[-1][0].endswith("CALIBRATION_APPROVED")
    app.run()  # Explicit refresh reads the newly registered selection-bound calibration.
    next(w for w in app.selectbox if w.label=="Conclusão humana para este desfecho").select("EVIDENCIA_INCONCLUSIVA")
    for w in app.text_area:
        if w.label in {"Justificativa da conclusão","Importância clínica","Incerteza e precisão","Consistência entre resultados","Limitações da síntese"}:w.set_value("Synthetic independent clinical judgment with limitations")
    next(w for w in app.checkbox if w.label.startswith("Conferi todos os resultados")).check()
    next(b for b in app.button if b.label=="Registrar conclusão clínica revisada").click().run()
    assert not app.exception and not app.error
    assert calls[-1][0].endswith("SYNTHESIS_CONCLUDED") and workspace.freeze()["groups"][0]["category"]=="EVIDENCIA_INCONCLUSIVA"


@pytest.mark.requirement("REQ-CLN-010")
def test_pending_pilot_forms_cannot_approve_or_conclude(workspace,monkeypatch):
    from streamlit.testing.v1 import AppTest
    from denguepharma_analytics import client
    calls=[]
    monkeypatch.setattr(client,"private",lambda path,**kwargs:calls.append(path) or view(workspace,ADJ))
    app=AppTest.from_string("from denguepharma_analytics.clinical.synthesis_ui import render\nrender('workspace','token')",default_timeout=30).run()
    assert not app.exception
    assert all(b.disabled for b in app.button) and len(app.button)==2
    assert calls==["/workspace/synthesis"] and any("Sem grupos de resultados revisados" in i.value for i in app.info)
