"""Datas e disponibilidade do registro, sem sobrevida de pacientes."""
import streamlit as st
from . import client


def render(run_id,manifest,summary):
    with st.expander("Relato de resultados — auditoria de datas"):
        if "reporting_registry" not in manifest["tables"]:
            st.info("Esta execução não contém a auditoria de datas. Selecione uma execução posterior.");return
        reporting=summary["reporting"];stats=reporting["interval_summary"]
        st.caption(reporting["notice"])
        st.write("Corte:",reporting["cutoff"],"· Registros:",reporting["trials"])
        if not reporting["trials"]:st.info("Sem registros para esta análise.");return
        st.write("Registros com status COMPLETED:",stats["completed"],"· Pares calculáveis:",stats["observed"])
        if stats["observed"]:
            st.write("Intervalo declarado em dias — mediana:",stats["median"],"· mínimo:",stats["min"],"· máximo:",stats["max"])
        else:st.info("Sem pares de datas que atendam ao protocolo; nenhum intervalo foi imputado.")
        st.warning("Intervalos apenas entre pares válidos declarados. Sem censura ou Kaplan–Meier; não são tempos de recuperação ou sobrevida de pacientes.")
        for name in ("reporting_results_by_status","reporting_availability","reporting_intervals"):
            st.dataframe(client.table(run_id,name,limit=1000)["rows"],hide_index=True,width="stretch")
        with st.expander("Datas, motivos de não cálculo e proveniência"):
            rows=client.table(run_id,"reporting_registry",limit=1000)
            st.dataframe(rows["rows"],hide_index=True,width="stretch")
            if rows["total"]>1000:st.caption("Visualização limitada a 1.000 registros; os CSVs contêm todas as linhas.")
        for name in manifest.get("figures",{}):
            if name.startswith("figures/reporting-"):st.image(client.base_url()+f"/api/public/analyses/{run_id}/artifacts?name={name}")
        for name in ("reporting_registry","reporting_availability","reporting_intervals","reporting_results_by_status"):
            st.link_button("CSV — "+name,client.base_url()+f"/api/public/analyses/{run_id}/artifacts?name={name}.csv")
