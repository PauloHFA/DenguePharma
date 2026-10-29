"""Interface explicita para pesquisa; votos independentes e formularios orientados pelo contrato."""
import json
from urllib.error import HTTPError, URLError
import streamlit as st
from .. import client
from .refresh import rerun_curation


def public(run_id,manifest,summary):
    st.subheader("Benefício, alívio de sintomas e segurança")
    clinical=summary.get("clinical",{})
    if clinical.get("document_integrity",{}).get("blocked_documents"):
        st.warning("Esta execução registra documentos suspensos por alerta humano de integridade. As aprovações anteriores não integram a síntese atual; consulte a curadoria para reavaliação.")
    if not clinical.get("reviewed_results"):
        st.warning("Sem resultados clínicos revisados. O piloto operacional não permite concluir quais fármacos beneficiam pacientes.")
    st.caption("Adultos e crianças separados; população mista identificada. Estudos observacionais em camada própria. Sem meta-análise ou ranking.")
    if "clinical_results" not in manifest["tables"]:
        st.info("Esta execução precede a emenda clínica. Selecione uma execução posterior."); return
    st.write("Situação da seleção:",clinical.get("screening_counts",{}))
    rows=client.table(run_id,"clinical_results",limit=1000)
    if rows["total"]>1000: st.caption("Visualização limitada a 1.000 resultados. Os CSVs contêm todas as linhas.")
    records=rows["rows"]
    for field,label in (("population","População"),("design_layer","Desenho"),("purpose","Finalidade"),("outcome_code","Desfecho")):
        choices=sorted({r[field] for r in records}); value=st.selectbox(label,[""]+choices,key="clinical_"+field,format_func=lambda v:v or "Todos")
        if value: records=[r for r in records if r[field]==value]
    if records:
        st.dataframe(records,hide_index=True,width="stretch")
        selected=st.selectbox("Ficha rastreável",range(len(records)),format_func=lambda n:records[n]["intervention"]+" / "+records[n]["study_id"]+" / "+records[n]["timepoint"])
        st.json(records[selected])
    for table,title in (("clinical_synthesis","Síntese e justificativas humanas"),("clinical_references","Fontes e localizadores"),("clinical_conflicts","Conflitos não resolvidos"),("clinical_absences","Ausência de estudo confirmada no corpus")):
        with st.expander(title):
            st.dataframe(client.table(run_id,table,limit=1000)["rows"],width="stretch")
    groups=client.table(run_id,"clinical_synthesis",limit=1000)["rows"]
    if groups:
        import pandas as pd
        st.subheader("Mapa de benefício e incerteza — julgamentos humanos")
        mapped=[{**json.loads(g["scope_json"]),"conclusao":g["category"]} for g in groups]
        palette={"BENEFICIO_SUSTENTADO":"#d8efdc","SINAL_DANO":"#f6d5d5","EVIDENCIA_INCONCLUSIVA":"#fff1bf","REVISAO_DA_SINTESE_PENDENTE":"#e5e7eb"}
        frame=pd.DataFrame(mapped)
        st.dataframe(frame.style.map(lambda v:"background-color:"+palette.get(v,"white"),subset=["conclusao"]),hide_index=True,width="stretch")
        st.caption("Cada linha mantém seu comparador e estrato completos. As cores representam decisões revisadas, sem pontuação, ordenação por eficácia ou fusão entre contextos.")
    for name in ("clinical_results","clinical_synthesis","clinical_references","clinical_screening"):
        st.link_button("CSV — "+name,client.base_url()+f"/api/public/analyses/{run_id}/artifacts?name={name}.csv")
    for name in manifest.get("figures",{}):
        if not name.startswith(("figures/calibration-","figures/sponsors-","figures/reporting-","figures/publication-refs-")): st.image(client.base_url()+f"/api/public/analyses/{run_id}/artifacts?name={name}")


@st.fragment
def curation():
    with st.expander("Curadoria clínica — acesso protegido"):
        st.caption("Usa as contas e permissões existentes. Esta área exige revisores distintos e adjudicador independente; os dashboards permanecem abertos.")
        try:
            if "clinical_token" not in st.session_state:
                with st.form("clinical_login"):
                    email=st.text_input("E-mail"); password=st.text_input("Senha",type="password")
                    if st.form_submit_button("Entrar na curadoria"):
                        result=client.private("/login",data={"email":email,"password":password})
                        st.session_state.clinical_token=result["token"]; rerun_curation()
                return
            if st.button("Sair da curadoria"):
                del st.session_state.clinical_token
                for session_key in list(st.session_state):
                    if session_key.startswith(("review_csv_","source_","extraction_","synthesis_","identity_","selection_","screen_","adjudicate_","integrity_")): del st.session_state[session_key]
                rerun_curation()
            token=st.session_state.clinical_token
            workspaces=client.private("/workspaces",token=token)
            if not workspaces: st.info("Inicialize o espaço privado pelo comando clinical-init."); return
            spaces={w["id"]:w for w in workspaces}
            key=st.selectbox("Espaço privado",list(spaces),format_func=lambda value:str(spaces[value].get("source_protocol",{}).get("code") or "Protocolo")+" · "+str(spaces[value].get("document_count","?"))+" documentos · "+value[:12])
            state=client.private(f"/{key}/state",token=token)
            from .review_ui import render as review_tools,source_tools
            review_tools(key,token)
            from .integrity_ui import render as integrity_form
            integrity_form(key,token)
            from .selection_flow_ui import render as selection_flow_form
            selection_flow_form(key,token)
            from .identity_ui import render as identity_form
            identity_form(key,token)
            from .screening_ui import render as screening_form
            screening_form(state,key,token)
            st.dataframe(state["queue"],width="stretch")
            st.caption("Os votos alheios não são exibidos ao revisor. Adjudicadores podem consultar conflitos; votes_hash aparece no campo adjudication da fila e pode ser obtido pela ação de diagnóstico restrita descrita no protocolo.")
            source_tools(key,token,state["sources"])
            from .extraction_ui import render as extraction_forms
            extraction_forms(state,key,token)
            from .extraction_coverage_ui import render as coverage_form
            coverage_form(key,token)
            from .synthesis_ui import render as synthesis_forms
            synthesis_forms(key,token)
            from .collection_ui import render as collection_form
            collection_form(key,token)
            with st.expander("Rascunhos, grupos e conflitos (privado)"): st.json({k:state[k] for k in ("candidates","groups","conflicts")})
            kind=st.selectbox("Ação de curadoria",["SCREENED","SCREEN_ADJUDICATED","DOCUMENT_LINKED","RESULT_DRAFTED","RESULT_REVIEWED","RESULT_ADJUDICATED","SYNTHESIS_CONCLUDED","CALIBRATION_APPROVED","ABSENCE_CONCLUDED"])
            st.caption("Preencha o JSON conforme analytics/examples/clinical-actions.json. IDs de eventos são retornados após salvar. Nenhum botão publica resultados automaticamente.")
            with st.expander("Contratos e campos aceitos pela API"):
                if st.button("Consultar contratos autenticados"): st.json(client.private("/contracts",token=token))
            with st.form("clinical_action"):
                payload=st.text_area("Dados da decisão (JSON)",value="{}",height=250)
                if st.form_submit_button("Registrar decisão auditável"):
                    result=client.private(f"/{key}/actions/{kind}",token=token,data=json.loads(payload)); st.success("Decisão registrada"); st.json(result)
        except HTTPError as error:
            try: detail=json.loads(error.read()).get("detail","")
            except (ValueError,UnicodeDecodeError): detail=""
            st.error(f"Operação recusada pela API ({error.code}). {detail if isinstance(detail,str) else ''} Confira permissão, independência e dados; nenhuma aprovação é inferida.")
        except (ValueError,URLError,TimeoutError,KeyError): st.error("Não foi possível concluir a operação. Verifique os dados e a conexão.")
