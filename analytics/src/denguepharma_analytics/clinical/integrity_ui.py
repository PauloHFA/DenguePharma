"""Explicit preview and confirmation of human documentary alerts."""
import streamlit as st
from .. import client
from ..domain import digest
from .refresh import rerun_curation


def render(key,token):
    with st.expander('Integridade documental — retratações e correções'):
        notice_key='integrity_notice_'+key
        if notice_key in st.session_state:st.success(st.session_state.pop(notice_key))
        state=client.private(f'/{key}/integrity',token=token)
        st.caption(state['notice'])
        st.write('Documentos com bloqueio ativo:',state['blocked_documents'])
        st.dataframe([{k:v for k,v in row.items() if k!='notice'} for row in state['documents']],hide_index=True,width='stretch')
        for row in state['documents']:
            if row['notice']:
                with st.expander('Alerta registrado — '+row['document_id']):st.json(row['notice'])
        if not state['can_edit']:
            st.info('Registrar ou regularizar alertas exige adjudicador ou administrador.');return
        docs={d['document_id']:d for d in state['documents']}
        document=st.selectbox('Documento do alerta',[None]+list(docs),format_func=lambda v:'Selecione explicitamente' if v is None else docs[v]['title'] or v,key='integrity_document_'+key)
        status=st.selectbox('Situação documental confirmada',[None,'EM_REAVALIACAO','RETIRADO','REGULARIZADO'],format_func=lambda v:v or 'Selecione explicitamente',key='integrity_status_'+key)
        category=st.selectbox('Tipo de alerta documental',[None,'RETRATACAO','CORRECAO_RELEVANTE','OUTRO_ALERTA_DOCUMENTAL'],format_func=lambda v:v or 'Selecione explicitamente',key='integrity_category_'+key)
        reference=st.text_input('Referência HTTPS do aviso conferido',key='integrity_reference_'+key)
        reason=st.text_area('Justificativa documental e material conferido',key='integrity_reason_'+key)
        payload=dict(document_id=document,status=status,category=category,source_reference=reference,reason=reason)
        session_key='integrity_preview_'+key
        if st.button('Conferir impacto do alerta',key='integrity_prepare_'+key,disabled=not document or not status or not category or len(reason.strip())<10 or not reference):
            st.session_state.pop(session_key,None)
            prepared=client.private(f'/{key}/integrity/preview',token=token,data=payload)
            st.session_state[session_key]=dict(preview=prepared,payload=payload,session_hash=digest(token.encode()))
        saved=st.session_state.get(session_key)
        if saved and (saved['payload']!=payload or saved['session_hash']!=digest(token.encode())):
            st.session_state.pop(session_key,None);saved=None
            st.warning('Alerta ou sessão alterado. Confira outra prévia antes de confirmar.')
        if saved:
            prepared=saved['preview']
            st.warning(prepared['warning'])
            st.json({k:prepared[k] for k in ('previous_status','study_id','current_votes_to_recheck','approved_results_to_recheck','synthesis_groups_to_recheck','calibration_to_recheck')})
            with st.form('integrity_confirm_'+key+prepared['receipt']):
                checked=st.checkbox('Conferi o aviso e o impacto; esta é uma decisão documental humana.')
                if st.form_submit_button('Confirmar alteração de integridade'):
                    if not checked:st.error('Confirme a conferência documental antes de registrar.')
                    else:
                        client.private(f'/{key}/integrity/confirm',token=token,data=dict(notice=prepared['notice'],receipt=prepared['receipt']))
                        st.session_state.pop(session_key,None)
                        st.session_state[notice_key]='Alerta registrado. A curadoria foi atualizada; atualizar o dashboard científico exige preparar e publicar uma nova execução.'
                        rerun_curation()
        if state['history']:
            with st.expander('Histórico de alertas documentais'):st.dataframe(state['history'],width='stretch')
