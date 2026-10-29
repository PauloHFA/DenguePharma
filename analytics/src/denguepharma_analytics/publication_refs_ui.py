"""Cobertura de referencias, sem confirmar resultados clinicos ou buscar artigos."""
import streamlit as st
from . import client


def render(run_id,manifest,summary):
    with st.expander("Publicações indicadas — cobertura por PMID"):
        if "publication_reference_links" not in manifest["tables"]:
            st.info("Esta execução não contém a auditoria de referências. Selecione uma execução posterior.");return
        data=summary["publication_references"]
        st.caption(data["notice"])
        st.write("Registros de ensaios:",data["registry_units"],"· Publicações no corpus:",data["publication_documents"])
        if not data["registry_units"]:st.info("Sem registros de ensaio para conferir referências.");return
        result=next(r for r in data["coverage"] if r["reference_type"]=="RESULT")
        if not result["registry_units_with_references"]:
            st.warning("Não há referência com tipo RESULT declarada neste snapshot. Isso não confirma ausência de publicação de resultados; confira também os outros tipos.")
        st.dataframe(data["coverage"],hide_index=True,width="stretch")
        for name,title in (("publication_reference_links","Referências, candidatos e proveniência"),("publication_reference_missing","PMIDs ainda não recuperados no corpus")):
            with st.expander(title):
                response=client.table(run_id,name,limit=1000)
                st.dataframe(response["rows"],hide_index=True,width="stretch",column_config={"source_url":st.column_config.LinkColumn("PubMed — consultar fonte")})
                if response["total"]>1000:st.caption("Visualização limitada a 1.000 linhas; exporte o CSV completo.")
        st.caption("Os links permitem consulta à fonte. O sistema não coleta esses artigos nem altera a curadoria automaticamente.")
        for name in manifest.get("figures",{}):
            if name.startswith("figures/publication-refs-"):st.image(client.base_url()+f"/api/public/analyses/{run_id}/artifacts?name={name}")
        for name in ("publication_reference_links","publication_reference_coverage","publication_reference_missing"):
            st.link_button("CSV — "+name,client.base_url()+f"/api/public/analyses/{run_id}/artifacts?name={name}.csv")
