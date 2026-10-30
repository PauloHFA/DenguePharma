"""Correction review displays explicit JSON values instead of mixed-type table cells."""
import json
import streamlit as st


def render(changes):
    st.caption(changes['notice'])
    def display(rows):
        if not rows:
            st.write('Nenhuma alteração nesta seção.');return
        st.dataframe([dict(campo=row['path'],antes=json.dumps(row['before'],ensure_ascii=False) if row['before_exists'] else 'CAMPO_AUSENTE',
            depois=json.dumps(row['after'],ensure_ascii=False) if row['after_exists'] else 'CAMPO_AUSENTE') for row in rows],hide_index=True,width='stretch')
    st.write('Campos do resultado:');display(changes['field_changes'])
    st.write('Vínculo e justificativa da correção:');display(changes['workflow_changes'])
    st.write('Referências alteradas:', 'Sim' if changes['references_changed'] else 'Não')
    if changes['references_changed']:
        st.json(dict(antes=changes['references_before'],depois=changes['references_after']))
