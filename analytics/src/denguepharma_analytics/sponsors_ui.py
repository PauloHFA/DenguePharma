"""Panorama publico de patrocinadores declarados, separado da sintese clinica."""
import streamlit as st
from . import client


def render(run_id,manifest,summary):
    with st.expander("Patrocinadores declarados nos registros"):
        if "corpus_sponsor_trials" not in manifest["tables"]:
            st.info("Esta execução não contém a análise de patrocinadores. Selecione uma execução posterior.");return
        sponsors=summary["sponsors"]
        st.caption(sponsors["notice"])
        st.write("Registros consolidados por NCT ou documento:",sponsors["trials"])
        if not sponsors["trials"]:st.info("Sem registros para esta análise.");return
        st.write("NCT ausente:",sponsors["missing_nct"],"· NCT inválido:",sponsors["invalid_nct"])
        st.dataframe(client.table(run_id,"corpus_sponsor_distributions",limit=1000)["rows"],hide_index=True,width="stretch")
        st.dataframe(client.table(run_id,"corpus_sponsor_completeness",limit=1000)["rows"],hide_index=True,width="stretch")
        with st.expander("Registros, valores originais e proveniência"):
            records=client.table(run_id,"corpus_sponsor_trials",limit=1000)
            st.dataframe(records["rows"],hide_index=True,width="stretch")
            if records["total"]>1000:st.caption("Visualização limitada a 1.000 linhas; exporte a tabela completa.")
        for name in manifest.get("figures",{}):
            if name.startswith("figures/sponsors-"):st.image(client.base_url()+f"/api/public/analyses/{run_id}/artifacts?name={name}")
        for name in ("corpus_sponsor_trials","corpus_sponsor_distributions","corpus_sponsor_completeness"):
            st.link_button("CSV — "+name,client.base_url()+f"/api/public/analyses/{run_id}/artifacts?name={name}.csv")
