"""Selection counts and explicit human categorization after a resolved exclusion."""
import streamlit as st
from .. import client
from .refresh import rerun_curation


def render(key, token):
    with st.expander('Fluxo da seleção e motivos de exclusão'):
        state = client.private(f'/{key}/selection-flow', token=token)
        st.caption(state['notice'])
        st.write('Documentos:', state['document_count'], '· Identidades atuais:', state['study_identity_count'])
        st.write('Situação das identidades:', state['statuses'])
        st.write('Seleção resolvida:', 'Sim' if state['selection_complete'] else 'Não')
        st.write('Exclusões sem motivo principal atual:', state['exclusions_without_current_reason'])
        st.dataframe(state['exclusion_reasons'], hide_index=True, width='stretch')
        if st.button('Preparar resumo privado da seleção', key='selection_export_' + key):
            content = client.private(f'/{key}/selection-flow/export', token=token, binary=True)
            st.download_button('Baixar resumo agregado JSON', content, file_name='selection-flow.json',
                mime='application/json', on_click='ignore')
        if not state['can_record']:
            st.info('Categorizar exclusões resolvidas exige adjudicador ou administrador.'); return
        studies = {s['study_id']: s for s in state['excluded_studies'] if s['can_record']}
        if not studies:
            st.info('Sem exclusões resolvidas disponíveis para categorizar.'); return
        study = st.selectbox('Exclusão resolvida a documentar', [None] + list(studies),
            format_func=lambda value: 'Selecione explicitamente' if value is None else studies[value]['title'] or value,
            key='selection_reason_study_' + key)
        if study is None: return
        row = studies[study]
        if row['annotation']:
            st.write('Motivo principal atual:', row['annotation'])
        labels = {r['category']: r['label'] for r in state['exclusion_reasons']}
        with st.form('selection_reason_' + key + study + row['resolution_hash']):
            category = st.selectbox('Motivo principal de exclusão', [None] + list(labels),
                format_func=lambda value: 'Selecione explicitamente' if value is None else labels[value])
            reason = st.text_area('Critério do protocolo e justificativa conferida')
            confirmed = st.checkbox('Conferi a exclusão resolvida e seu motivo principal nas fontes e no protocolo.')
            if st.form_submit_button('Registrar motivo de exclusão'):
                if not category or len(reason.strip()) < 10 or not confirmed:
                    st.error('Selecione o motivo, justifique e confirme a conferência humana.'); return
                client.private(f'/{key}/actions/EXCLUSION_REASON_RECORDED', token=token,
                    data=dict(study_id=study, resolution_hash=row['resolution_hash'], category=category, reason=reason))
                st.success('Motivo registrado. A seleção independente e a calibração não foram alteradas.')
                rerun_curation()
