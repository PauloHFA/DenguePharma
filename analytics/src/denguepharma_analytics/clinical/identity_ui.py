"""Conferencia manual da identidade, com previa e confirmacao independentes da triagem."""
import streamlit as st
from .. import client
from ..domain import digest
from .refresh import rerun_curation


def render(key,token):
    with st.expander("Identidade dos estudos — documentos e vínculos"):
        state=client.private(f"/{key}/identity",token=token)
        st.caption(state["notice"])
        st.dataframe(state["documents"],hide_index=True,width="stretch")
        if not state["can_edit"]:
            st.info("Alterar vínculos exige papel de adjudicador ou administrador.");return
        if not state["documents"]:st.info("Sem documentos para conferir.");return
        preview_key="identity_preview_"+key;notice_key="identity_notice_"+key
        if notice_key in st.session_state:st.success(st.session_state.pop(notice_key))
        documents={d["document_id"]:d for d in state["documents"]}
        document=st.selectbox("Documento a vincular",[""]+list(documents),format_func=lambda v:(documents[v].get("title") or v)+" · "+v if v else "Selecione um documento",key="identity_document_"+key)
        current=documents[document]["study_id"] if document else None
        targets=[s["study_id"] for s in state["studies"] if s["study_id"]!=current or (document and documents[document]["needs_identity_review"])]
        target=st.selectbox("Estudo de destino",[""]+targets,format_func=lambda v:v or "Selecione o estudo conferido",key="identity_target_"+key+document)
        reason=st.text_area("Justificativa do vínculo e fontes conferidas",key="identity_reason_"+key+document)
        payload=dict(document_id=document,study_id=target,reason=reason)
        if st.button("Conferir impacto do vínculo",key="identity_prepare_"+key,disabled=not document or not target or len(reason.strip())<5):
            st.session_state.pop(preview_key,None)
            preview=client.private(f"/{key}/identity/preview",token=token,data=payload)
            st.session_state[preview_key]=dict(preview=preview,payload=payload,session_hash=digest(token.encode()))
        saved=st.session_state.get(preview_key)
        if saved is not None and (saved["payload"]!=payload or saved["session_hash"]!=digest(token.encode())):
            st.session_state.pop(preview_key,None);saved=None
            st.warning("Vínculo ou sessão alterados. Confira outra prévia antes de confirmar.")
        if saved is not None:
            preview=saved["preview"]
            st.warning("Confirmar altera a identidade dos estudos afetados e exige nova revisão de suas bases. Os votos não são transferidos.")
            st.write("Estudos/identidades antes e depois:",preview["studies_before"],preview["studies_after"])
            st.dataframe(preview["impacts"],hide_index=True,width="stretch")
            st.caption(preview["notice"])
            with st.form("identity_confirm_"+key+preview["receipt"]):
                checked=st.checkbox("Conferi os documentos, o estudo de destino e o impacto sobre a revisão.")
                if st.form_submit_button("Confirmar vínculo documental auditável"):
                    if not checked:st.error("Confirme a conferência documental antes de alterar o vínculo.")
                    else:
                        result=client.private(f"/{key}/identity/confirm",token=token,data=dict(link=preview["link"],receipt=preview["receipt"]))
                        st.session_state.pop(preview_key,None)
                        st.session_state[notice_key]="Vínculo registrado: "+result["event_id"]+". Confira novamente a seleção dos estudos afetados."
                        rerun_curation()
        with st.expander("Histórico de vínculos documentais"):
            st.dataframe(state["history"],hide_index=True,width="stretch")
