"""Calibracao e conclusoes humanas por campos, sem assumir eficacia."""
import streamlit as st
from pydantic import ValidationError
from .. import client
from .models import Calibration,Conclusion,Absence


def submit(key,token,kind,model,data):
    try:
        payload=model.model_validate(data).model_dump()
        result=client.private(f"/{key}/actions/{kind}",token=token,data=payload)
        st.success("Decisão registrada. Atualize o estado antes de continuar; publicação exige nova execução explícita.")
        st.json(result)
    except ValidationError as error:
        for item in error.errors():st.error(".".join(str(p) for p in item["loc"])+": "+item["msg"])


def render(key,token):
    state=client.private(f"/{key}/synthesis",token=token)
    with st.expander("Calibração da busca — decisão humana"):
        st.write("Seleção independente resolvida:","Sim" if state["selection_complete"] else "Não")
        st.write("Calibração vigente:","Aprovada" if state["calibration_approved"] else "Pendente")
        st.caption("Aprovar exige seleção resolvida e papel de adjudicador. Referências sentinela devem ser conferidas, com limitações e ajustes documentados. Aprovação local não inicia coleta completa nem equivale a registro externo.")
        studies={s["study_id"]:s for s in state["studies"]}
        with st.form("synthesis_calibration_"+key+state["selection_hash"]):
            sentinels=st.multiselect("Referências sentinela conferidas",list(studies),format_func=lambda i:(studies[i].get("title") or i)+" · "+studies[i]["status"])
            reason=st.text_area("Achados da calibração, limitações da busca e ajustes necessários")
            confirmed=st.checkbox("Conferi as referências e os critérios; esta é uma decisão metodológica humana.")
            if st.form_submit_button("Registrar aprovação da calibração",disabled=not state["can_approve_calibration"]):
                if not confirmed:st.error("Confirme a conferência humana antes de registrar.")
                else:submit(key,token,"CALIBRATION_APPROVED",Calibration,dict(selection_hash=state["selection_hash"],sentinel_ids=sentinels,reason=reason))
        if state["calibration"]:
            with st.expander("Calibração registrada para a seleção atual"):st.json(state["calibration"])
    with st.expander("Síntese clínica por desfecho — julgamento humano"):
        st.caption(state["notice"])
        for blocker in state["blockers"]:st.info(blocker)
        groups={g["scope_id"]:g for g in state["groups"]}
        if not groups:st.info("Sem grupos de resultados revisados para concluir. Ausência de resultados revisados não é evidência inconclusiva nem ausência de estudo.")
        else:
            selected=st.selectbox("Comparação e estrato revisados",list(groups),format_func=lambda i:groups[i]["scope"]["intervention"]+" / "+groups[i]["scope"]["population"]+" / "+groups[i]["scope"]["outcome_code"]+" / "+groups[i]["scope"]["timepoint"],key="synthesis_group_"+key)
            group=groups[selected]
            st.write("Estudos distintos:",group["study_count"]);st.json(group["scope"])
            st.dataframe([{k:r.get(k) for k in ("study_id","comparison_id","measure","estimate","ci_low","ci_high","confidence_level","risk_of_bias","limitations")} for r in group["results"]],hide_index=True,width="stretch")
            st.caption("Não somar participantes entre comparações potencialmente sobrepostas. Significância isolada, quantidade de artigos e completude não determinam a categoria.")
            with st.form("synthesis_conclusion_"+key+selected+group["result_set_hash"]+state["selection_hash"]):
                category=st.selectbox("Conclusão humana para este desfecho",[None]+group["available_categories"],format_func=lambda v:v or "Selecione após revisar")
                data=dict(selection_hash=state["selection_hash"],scope=group["scope"],result_set_hash=group["result_set_hash"],category=category)
                for field,label in (("rationale","Justificativa da conclusão"),("clinical_importance","Importância clínica"),("uncertainty","Incerteza e precisão"),("consistency","Consistência entre resultados"),("limitations","Limitações da síntese")):
                    data[field]=st.text_area(label)
                confirmed=st.checkbox("Conferi todos os resultados e limitações deste grupo.")
                if st.form_submit_button("Registrar conclusão clínica revisada",disabled=not group["can_conclude"]):
                    if not confirmed:st.error("Confirme a revisão do grupo antes de registrar.")
                    else:submit(key,token,"SYNTHESIS_CONCLUDED",Conclusion,data)
            if group["judgment"]:
                with st.expander("Conclusão vigente e justificativas"):st.json(group["judgment"])
    with st.expander("Ausência de estudo elegível no corpus — conferência humana"):
        st.caption("Usar somente após seleção completa e calibração vigente. Um estudo misto pode representar adultos e crianças; falta de extração não permite concluir ausência de estudo. Esta categoria não afirma ausência na literatura.")
        with st.form("synthesis_absence_"+key+state["selection_hash"]):
            intervention=st.text_input("Intervenção cuja ausência foi conferida")
            population=st.selectbox("População da ausência conferida",state["populations"])
            reason=st.text_area("Justificativa e limites da ausência no corpus")
            confirmed=st.checkbox("Conferi o corpus selecionado; não estou confundindo dado não extraído com ausência de estudo.")
            if st.form_submit_button("Registrar ausência no corpus",disabled=not state["can_conclude_absence"]):
                if not confirmed:st.error("Confirme a conferência antes de registrar.")
                else:submit(key,token,"ABSENCE_CONCLUDED",Absence,dict(selection_hash=state["selection_hash"],intervention=intervention,population=population,reason=reason))
