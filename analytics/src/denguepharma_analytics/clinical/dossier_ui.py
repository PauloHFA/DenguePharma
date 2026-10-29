"""Show only source representations belonging to the selected study."""
import streamlit as st
from .. import client


def render(key, token, row):
    from urllib.parse import quote
    study = quote(row['study_id'], safe='')
    dossier = client.private(f"/{key}/studies/{study}/dossier?basis_hash={row['basis_hash']}", token=token)
    with st.expander('Documentos do estudo selecionado — leitura para triagem'):
        st.caption(dossier['notice'])
        if dossier.get('integrity_alerts'):
            st.warning('Há documento com alerta humano de integridade neste estudo. Inclusão e resultados ficam bloqueados até regularização documentada.')
            st.json(dossier['integrity_alerts'])
        if dossier['unresolved_identity_documents']:
            st.warning('Identidade documental ambígua: confira os vínculos antes de decidir pela inclusão.')
        for document in dossier['documents']:
            st.write(document['title'] or document['document_id'])
            st.json({k: v for k, v in document.items() if k != 'source_versions'})
        versions = {v['version_id']: v for d in dossier['documents'] for v in d['source_versions']}
        if not versions:
            st.info('Sem representação textual neste estudo. Não preencher informação ausente por inferência.')
            return
        selected = st.selectbox('Fonte deste estudo', list(versions),
            format_func=lambda v: versions[v]['document_id'] + ' · ' + v,
            key='source_dossier_version_' + key + row['study_id'])
        metadata = versions[selected]
        st.json(metadata)
        if st.checkbox('Ler texto normalizado desta versão', key='source_dossier_open_' + key + selected):
            source = client.private(f"/{key}/sources/{quote(selected, safe='')}", token=token)
            if any(source[name] != metadata[name] for name in ('document_id', 'text_hash', 'content_hash')):
                st.error('A versão consultada diverge do dossiê. Atualize a página antes de revisar.')
                return
            st.text(source['text'])
            st.caption('O texto normalizado pode conter somente metadados ou resumo. '
                'Use o gerador de localizadores na área de fontes para registrar trechos verificáveis.')
