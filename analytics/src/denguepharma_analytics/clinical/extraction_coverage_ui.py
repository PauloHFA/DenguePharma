"""Private outcome-workflow map; no missing values are promoted to findings."""
import streamlit as st
from .. import client


def render(key,token):
    with st.expander('Cobertura da extração por desfecho'):
        state=client.private(f'/{key}/extraction-coverage',token=token)
        st.caption(state['notice'])
        st.write('Estudos/identidades incluídos:',state['included_studies'])
        st.write('Desfechos do protocolo:',state['protocol_outcomes'])
        st.write('Calibração vigente:', 'Aprovada' if state['calibration_approved'] else 'Pendente')
        if not state['cells']:
            st.info('Sem estudos incluídos na seleção atual. O mapa permanece vazio; conclua a revisão independente antes da extração.')
        else:
            st.write('Células com resultado revisado:',state['cells_with_reviewed_results'],
                '· Sem resultado revisado:',state['cells_without_reviewed_results'],
                '· Com conflito:',state['cells_with_conflicts'])
            status=st.selectbox('Situação no mapa de extração',['TODAS','SEM_RESULTADO_REVISADO','CONFLITO_PENDENTE','COM_RESULTADO_REVISADO'],key='extraction_coverage_filter_'+key)
            rows=[c for c in state['cells'] if status=='TODAS' or c['status']==status]
            st.dataframe(rows,hide_index=True,width='stretch')
            st.caption('As contagens descrevem a extração na base atual. Não representam a proporção de desfechos aplicáveis ou evidência de benefício.')
        if st.button('Preparar pacote de cobertura',key='extraction_coverage_export_'+key):
            content=client.private(f'/{key}/extraction-coverage/export',token=token,binary=True)
            st.download_button('Baixar mapa CSV, resumo e manifesto',content,file_name='extraction-coverage.zip',mime='application/zip',on_click='ignore')
