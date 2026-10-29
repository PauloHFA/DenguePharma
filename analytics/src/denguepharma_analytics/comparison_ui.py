"""Atualizacoes do corpus publicado; nao mede efeito de medicamentos."""
import json
from urllib.error import HTTPError
from urllib.parse import urlencode
import pandas as pd
import streamlit as st
from . import client


def render(run_id,runs):
    with st.expander("Atualizações entre execuções"):
        current=next(r for r in runs if r["id"]==run_id)
        candidates=[r for r in runs if r["id"]!=run_id and r["protocol"].get("id")==current["protocol"].get("id")]
        st.caption("Documentos de origem por ID persistido. Mudanças de software, de conteúdo e de representação são distintas. A compatibilidade completa é conferida pela API.")
        if not candidates:st.info("Sem outra execução publicada para o mesmo protocolo.");return
        by_id={r["id"]:r for r in candidates}
        baseline=st.selectbox("Execução de referência da comparação",[""]+list(by_id),format_func=lambda v:v[:12]+" · "+str(by_id[v]["document_count"])+" documentos" if v else "Selecione a referência",key="comparison_baseline_"+run_id)
        if st.button("Comparar execuções publicadas",disabled=not baseline,key="comparison_prepare_"+run_id):
            query=urlencode(dict(baseline=baseline,current=run_id))
            try:result=client.get("/api/public/comparisons?"+query)
            except HTTPError as error:
                try:detail=json.loads(error.read()).get("detail","")
                except (ValueError,UnicodeDecodeError):detail=""
                st.error("Comparação recusada. "+(detail if isinstance(detail,str) else "Confira as execuções."));return
            st.write(f"Documentos de origem: {result['baseline_documents']} → {result['current_documents']}; IDs compartilhados: {result['shared_documents']}.")
            st.caption(result["notice"])
            if result["same_input"]:st.info("Mesma entrada congelada. Diferenças nas tabelas podem decorrer do processamento; não significam nova coleta.")
            frame=pd.DataFrame(result["metrics"])
            st.bar_chart(frame.set_index("change_kind")[["count"]])
            st.dataframe(result["metrics"],hide_index=True,width="stretch")
            st.subheader("Documentos novos ou alterados e não observados")
            if result["document_changes"]:st.dataframe(result["document_changes"],hide_index=True,width="stretch")
            else:st.info("Nenhuma alteração nos documentos de origem entre estas execuções.")
            st.dataframe(result["table_changes"],hide_index=True,width="stretch")
            st.code(result["comparison_id"],language=None)
            for name in ("comparison.json","document_changes.csv","table_changes.csv","manifest.json"):
                st.link_button("Baixar comparação — "+name,client.base_url()+"/api/public/comparisons/artifacts?"+query+"&name="+name)
