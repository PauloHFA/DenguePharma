"""Interface publica da fundacao; formularios de curadoria ainda estao no legado."""
import os
import json
from urllib.error import HTTPError, URLError

import pandas as pd
import streamlit as st
from denguepharma_analytics import client

st.set_page_config(page_title="DenguePharma Analytics", page_icon="📊", layout="wide")
st.title("DenguePharma Analytics")
st.caption("Pesquisa farmacológica sobre dengue · ciência de dados reproduzível")
st.info("Panorama de registros coletados e evidências revisadas são camadas distintas. Frequência não mede eficácia. Uso em pesquisa, sem recomendação terapêutica.")


def show_table(run_id, name, title, **filters):
    st.subheader(title)
    key = run_id + name
    page = int(st.number_input("Página — " + title, min_value=1, value=1, step=1, key=key))
    result = client.table(run_id, name, offset=(page-1)*100, **filters)
    if result["total"] == 0:
        st.write("Sem dados nesta camada.")
    else:
        st.caption(f'Exibindo {len(result["rows"])} de {result["total"]} linhas. Os filtros abaixo se aplicam à tabela identificada.')
        st.dataframe(pd.DataFrame(result["rows"]), hide_index=True, width="stretch")
    st.link_button("Baixar tabela CSV — "+title, client.base_url()+f"/api/public/analyses/{run_id}/artifacts?name={name}.csv")


try:
    runs = client.get("/api/public/analyses")
    if not runs:
        st.warning("Nenhuma execução publicada. Prepare os dados e publique explicitamente pelo comando Python.")
    else:
        by_id = {r["id"]: r for r in runs}
        run_id = st.selectbox("Execução publicada", list(by_id), format_func=lambda key: str(by_id[key]["protocol"].get("code"))+" · "+key[:12])
        summary = client.get(f"/api/public/analyses/{run_id}/summary")
        manifest = client.get(f"/api/public/analyses/{run_id}")
        metrics = st.columns(4)
        for column, label, value in zip(metrics, ["Documentos coletados", "Publicações", "Registros de ensaios", "Estudos revisados"],
                                         [summary["documentCount"], summary["publicationCount"], summary["trialCount"], summary["studyCount"]]): column.metric(label, value)
        st.caption(f'Corte: {summary["protocol"].get("cutoff_date")} · Hash de entrada: {manifest["input_hash"]}')
        if summary["protocol"].get("maxRecordsPerSource", 0): st.warning("Piloto operacional: amostra de conveniência, com elegibilidade pendente. Não substitui calibração metodológica ou teste independente.")
        overview, trials, reviewed, quality, future, clinical, general = st.tabs(["Corpus coletado", "Ensaios", "Evidências revisadas", "Qualidade e reprodução", "Eixos do PDF", "Sintese clinica", "Resultados gerais"])
        with general:
            from denguepharma_analytics.clinical.calibration_ui import public as general_results
            general_results(run_id,manifest,summary)
        with overview:
            temporal = client.table(run_id, "corpus_temporal", limit=1000)["rows"]
            if temporal:
                frame = pd.DataFrame(temporal); valid = frame[frame.category.str.fullmatch(r"\d{4}")].copy()
                if len(valid):
                    valid["ano"] = valid.category.astype(int)
                    st.line_chart(valid.pivot(index="ano", columns="field", values="count").sort_index())
                    st.caption("Contagens anuais: publicações por ano bibliográfico e registros por ano de início. Unidades e denominadores na tabela.")
            if summary["temporalFlags"]: st.warning(f'{len(summary["temporalFlags"])} registros têm ano bibliográfico posterior ao corte; conferir na fonte.')
            show_table(run_id, "corpus_temporal", "Distribuição temporal")
            sources = sorted({row["category"] for row in summary["distributions"] if row["field"] == "sources"})
            source = st.selectbox("Fonte da tabela de documentos", [""]+sources, format_func=lambda value: value or "Todas")
            show_table(run_id, "corpus_documents", "Documentos e identificadores", source=source)
        with trials:
            from denguepharma_analytics.reporting_ui import render as reporting_audit
            reporting_audit(run_id,manifest,summary)
            from denguepharma_analytics.sponsors_ui import render as sponsor_panorama
            sponsor_panorama(run_id,manifest,summary)
            show_table(run_id, "corpus_distributions", "Distribuições dos registros coletados")
            show_table(run_id, "corpus_enrollment", "Participantes previstos e efetivos — sem somatório")
        with reviewed:
            if summary["studyCount"] == 0: st.warning("Sem estudos com campos científicos revisados. O panorama científico permanece vazio.")
            context = st.selectbox("Contexto revisado", ["", "HUMANO", "DESAFIO_CONTROLADO", "IN_VITRO", "IN_SILICO", "ANIMAL"], format_func=lambda value: value or "Todos")
            show_table(run_id, "mart_panorama", "Panorama por estudo revisado", context=context)
            show_table(run_id, "reviewed_completeness", "Completude dos campos revisados")
        with quality:
            from denguepharma_analytics.publication_refs_ui import render as publication_coverage
            publication_coverage(run_id,manifest,summary)
            from denguepharma_analytics.comparison_ui import render as compare_runs
            compare_runs(run_id,runs)
            show_table(run_id, "corpus_completeness", "Disponibilidade dos metadados")
            show_table(run_id, "corpus_links", "Vínculos confirmados")
            st.caption("A tabela anterior conserva vínculos legados por identidade compartilhada; isso não substitui a conferência do vínculo clínico entre publicação e registro.")
            show_table(run_id, "corpus_link_candidates", "Vínculos candidatos para revisão")
            for warning in summary["warnings"]: st.write("• "+warning)
            st.link_button("Manifesto de reprodução", client.base_url()+f"/api/public/analyses/{run_id}/artifacts?name=manifest.json")
            st.link_button("Relatório Quarto HTML", client.base_url()+f"/api/public/analyses/{run_id}/artifacts?name=report.html")
            st.link_button("Panorama revisado em Parquet", client.base_url()+f"/api/public/analyses/{run_id}/artifacts?name=gold/mart_panorama.parquet")
        with clinical:
            from denguepharma_analytics.clinical.ui import public
            public(run_id,manifest,summary)
        with future:
            capabilities = client.get("/api/capabilities")
            for axis, info in capabilities["axes"].items(): st.write(f'Eixo {axis}: {info["state"]} — {info.get("description", "Panorama descritivo parcial; inferência ainda planejada")}')
            st.info("A avaliação de IA exige referência adjudicada e protocolo próprio. Dados de carga e análise de sobrevivência ainda não foram implementados.")
except (HTTPError, URLError, TimeoutError, ValueError, KeyError) as error:
    st.error("Não foi possível consultar a API de análises. Verifique a execução do serviço e a integridade dos dados.")

st.divider()
st.caption("Migração em paralelo: coletores e autenticação permanecem no legado. A curadoria clínica possui área privada própria, com revisão independente.")
st.link_button("Área de curadoria legada", os.getenv("LEGACY_CURATOR_URL", "http://127.0.0.1:5173/curadoria"))

from denguepharma_analytics.clinical.ui import curation
curation()
