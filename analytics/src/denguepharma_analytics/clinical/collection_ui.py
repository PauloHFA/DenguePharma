"""Plano privado de coleta; nenhuma chamada de coleta a partir de um simples rerun."""
import streamlit as st
from .. import client


def render(key,token):
    with st.expander("Coleta completa — plano e pré-requisitos"):
        state=client.private(f"/{key}/collection-plan",token=token)
        st.caption(state["notice"])
        if not state["ready"]:
            st.warning("Coleta completa bloqueada. Resolver seleção independente e calibração antes de ampliar a busca.")
            for reason in state["blockers"]:st.write("• "+reason)
        else:st.success("Pré-requisitos locais conferidos. A execução exige operador autenticado e o identificador deste plano.")
        config=state["configuration"]
        st.write("Corte calibrado:",config["cutoff"])
        st.write("Fontes:",config["sources"])
        st.write("Limite de registros por fonte: sem limite de piloto (maxRecords=0).")
        st.code(state["configuration_hash"],language=None)
        if state["ready"]:
            st.code("analytics/.venv/Scripts/python.exe -m denguepharma_analytics.cli clinical-collect-full --workspace "+key+" --collection "+state["configuration_hash"],language="powershell")
            st.caption("Cada chamada avança uma etapa curta ou consulta o processamento existente. Repetir o comando retoma os IDs conhecidos. Publicação e revisão do novo corpus permanecem separadas.")
