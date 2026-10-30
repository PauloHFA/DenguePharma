"""Ferramentas privadas de revisao. Sem cache global ou criacao automatica de votos."""
import streamlit as st
from .. import client
from ..domain import digest
from .refresh import rerun_curation


def import_form(key,token):
    state_key="review_csv_preview_"+key
    notice_key="review_csv_notice_"+key
    if notice_key in st.session_state:st.success(st.session_state.pop(notice_key))
    with st.form("review_import_"+key):
        uploaded=st.file_uploader("Planilha de triagem preenchida (CSV UTF-8)",type=["csv"],key="review_csv_"+key)
        if st.form_submit_button("Conferir prévia sem gravar decisões"):
            st.session_state.pop(state_key,None)
            if uploaded is None:st.error("Selecione sua planilha para conferir.")
            else:
                preview=client.private(f"/{key}/screening/preview",token=token,raw=uploaded.getvalue())
                st.session_state[state_key]=dict(result=preview,session_hash=digest(token.encode()))
    saved=st.session_state.get(state_key)
    if saved is None:return
    preview=saved["result"]
    if uploaded is None or digest(uploaded.getvalue())!=preview["content_hash"] or saved["session_hash"]!=digest(token.encode()):
        st.session_state.pop(state_key,None)
        st.warning("Planilha ou sessão alterada. Confira uma nova prévia antes de importar.");return
    st.info(f"Prévia: {preview['would_create']} novas decisões; {preview['would_update']} alterações; {preview['unchanged']} idênticas; {preview['skipped']} linhas em branco.")
    st.dataframe(preview["changes"],hide_index=True,width="stretch")
    st.caption(preview["notice"])
    with st.form("review_confirm_"+key+preview["receipt"]):
        confirmed=st.checkbox("Conferi esta prévia e confirmo que as decisões são minha revisão independente das fontes permitidas.")
        if st.form_submit_button("Confirmar e importar minhas decisões"):
            if not confirmed:st.error("Confirme a conferência e a autoria da revisão antes de importar.")
            else:
                result=client.private(f"/{key}/screening/import?expected_preview="+preview["receipt"],token=token,raw=uploaded.getvalue())
                st.session_state.pop(state_key,None)
                st.session_state[notice_key]=f"Decisões registradas: {result['imported']}; já idênticas: {result['unchanged']}; linhas em branco: {result['skipped']}. Calibração e publicação continuam separadas."
                rerun_curation()


def render(key,token):
    with st.expander("Preparar e acompanhar a revisão do piloto",expanded=True):
        state=client.private(f"/{key}/progress",token=token)
        st.write(f"**{state['studies']} estudos/identidades na fila**, {state['documents']} documentos. **{state['missing_independent_votes']} votos independentes ainda faltam**; {state['unresolved_studies']} identidades permanecem sem seleção resolvida.")
        mine=state.get("my_review")
        if mine:
            st.write(f"**Sua conta: {mine['available_tasks']} revisões disponíveis**, sendo {mine['first_reviews_pending']} iniciais e {mine['reassessments_pending']} reavaliações. **{mine['current_registered']} revisões registradas na base atual**; {mine['occupied_slots']} identidades com duas vagas já ocupadas.")
            st.caption(mine["notice"])
        st.write("Seleção:",state["screening_counts"])
        st.write("Calibração aprovada para a seleção atual:","Sim" if state["calibration_approved"] else "Não")
        st.caption(state["notice"])

        # Métricas de concordância inter-avaliadores (Etapa 0.22.0)
        try:
            agreement = client.private(f"/{key}/screening/agreement", token=token)
            if agreement and agreement.get("valid_paired_studies", 0) > 0:
                st.markdown("#### Concordância Inter-Avaliadores (Triagem Duplo-Cega)")
                col1, col2, col3 = st.columns(3)
                col1.metric("Concordância Observada (Po)", f"{agreement['observed_agreement'] * 100:.1f}%")
                col2.metric("Kappa de Cohen", f"{agreement['cohen_kappa']:.3f}" if agreement.get("cohen_kappa") is not None else "N/A", help=f"Classificação: {agreement['interpretation_kappa']}")
                col3.metric("AC1 de Gwet", f"{agreement['gwet_ac1']:.3f}" if agreement.get("gwet_ac1") is not None else "N/A", help=f"Classificação: {agreement['interpretation_ac1']}")
                st.caption(f"{agreement['valid_paired_studies']} estudos com votos pareados. {agreement['notice']}")
                with st.expander("Matriz de contingência (Revisor 1 vs Revisor 2)"):
                    matrix = agreement["contingency_matrix"]
                    st.table({row: matrix[row] for row in agreement["categories"]})
        except Exception:
            pass

        if state.get("unresolved_identity_documents"):
            st.warning(f"{state['unresolved_identity_documents']} documentos com identidade ambígua. Conferir os vínculos antes de aprovar a calibração.")
        if st.button("Preparar pacote de revisão independente",key="review_package_"+key):
            content=client.private(f"/{key}/review-package",token=token,binary=True)
            st.download_button("Baixar planilha, referências e protocolo",content,file_name="independent-review.zip",mime="application/zip",on_click="ignore")
        st.caption("Cada revisor preenche sua própria planilha. O pacote não contém votos alheios, resumos nem textos integrais. Campos humanos começam vazios.")
        import_form(key,token)


def source_tools(key,token,versions):
    with st.expander("Fontes permitidas e localizadores"):
        if not versions: st.info("Sem representações documentais disponíveis."); return
        by_id={v["version_id"]:v for v in versions}
        version=st.selectbox("Versão documental",list(by_id),format_func=lambda v:by_id[v]["document_id"][:12]+" · "+v,key="source_version_"+key)
        if not st.checkbox("Exibir texto normalizado da fonte",key="source_open_"+key+version): return
        source=client.private(f"/{key}/sources/{version}",token=token)
        st.json({k:v for k,v in source.items() if k!="text"});st.text(source["text"])
        length=len(source["text"])
        st.caption(f"{length} caracteres. Posições contam caracteres Unicode no texto normalizado; início inclusivo e fim exclusivo. Presença literal exige conferência semântica humana.")
        if not length: return
        with st.form("locator_"+key+version):
            field=st.text_input("Campo sustentado pelo trecho",placeholder="Ex.: treatment.n, timepoint ou population")
            start=st.number_input("Início do trecho",min_value=0,max_value=length-1,value=0,step=1)
            end=st.number_input("Fim do trecho (exclusivo)",min_value=1,max_value=length,value=min(length,100),step=1)
            if st.form_submit_button("Gerar referência literal"):
                if not field.strip() or end<=start: st.error("Informe o campo e um intervalo válido.")
                else:
                    ref=client.private(f"/{key}/locators",token=token,data=dict(version_id=version,field=field,start=int(start),end=int(end)))
                    st.json(ref["reference"]);st.caption(ref["notice"])
