"""Apresentacao publica de resultados descritivos; curadoria permanece independente."""
import streamlit as st
from .. import client


def public(run_id,manifest,summary):
    st.subheader("Resultados gerais da pesquisa — corpus coletado")
    calibration=summary.get("calibration")
    if not calibration:
        st.info("Esta execução antecede o diagnóstico de calibração. Selecione uma execução mais recente."); return
    st.info(calibration["notice"])
    st.write(f"**{summary['documentCount']} documentos:** {summary['publicationCount']} publicações e {summary['trialCount']} registros de ensaio. **{summary.get('clinical',{}).get('reviewed_results',0)} resultados clínicos revisados.**")
    rows=[{"Indicador":r["field"],"Categoria":r["category"],"Registros":r["count"],"Denominador":r["denominator"]} for r in summary["distributions"] if r["field"] in {"design","recruitment","has_results"}]
    st.dataframe(rows,hide_index=True,width="stretch")
    st.caption("Desenho, recrutamento e presença de resultados são metadados declarados na fonte; incluem registros ainda não selecionados para a pergunta clínica.")
    st.subheader("O que precisa ser conferido na calibração")
    st.dataframe([{"Sinal":r["label"],"Documentos":r["count"],"Denominador":r["denominator"]} for r in calibration["signals"]],hide_index=True,width="stretch")
    st.write(f"{calibration['documents_with_signals']}/{calibration['documents']} documentos têm pelo menos um sinal. Os sinais se sobrepõem; documentos sem sinal também precisam de revisão.")
    for name in manifest.get("figures",{}):
        if name.startswith("figures/calibration-"): st.image(client.base_url()+f"/api/public/analyses/{run_id}/artifacts?name={name}")
    with st.expander("Documentos e sinais para conferência"):
        page=int(st.number_input("Página dos documentos de calibração",min_value=1,value=1,step=1))
        documents=client.table(run_id,"calibration_documents",offset=(page-1)*100,limit=100)
        st.caption(f"{len(documents['rows'])} de {documents['total']} documentos. As referências e os sinais constam do CSV completo.")
        st.dataframe(documents["rows"],hide_index=True,width="stretch",column_config={"source_url":st.column_config.LinkColumn("Fonte original")})
    with st.expander("Tipos de intervenção e execução das buscas"):
        st.dataframe(calibration["intervention_types"],hide_index=True,width="stretch")
        st.caption("Tipos declarados no registro. BIOLOGICAL pode incluir vacinas; OTHER e procedimentos não são classificados como fármacos.")
        st.dataframe(calibration["searches"],hide_index=True,width="stretch")
        st.caption("Totais informados pelas buscas na coleta registrada, sem somar fontes como estudos únicos. Fração recuperada não mede representatividade, elegibilidade ou sensibilidade.")
    st.link_button("Baixar resultados gerais em Markdown",client.base_url()+f"/api/public/analyses/{run_id}/artifacts?name=research_findings.md")
    st.link_button("Baixar documentos e sinais em CSV",client.base_url()+f"/api/public/analyses/{run_id}/artifacts?name=calibration_documents.csv")
    st.link_button("Relatório científico HTML",client.base_url()+f"/api/public/analyses/{run_id}/artifacts?name=report.html")
    if not summary.get("clinical",{}).get("reviewed_results"):
        st.warning("Ainda não é possível concluir quais medicamentos beneficiam, prejudicam ou permanecem inconclusivos para pacientes. Primeiro, revisar e calibrar o piloto; depois, obter e revisar os resultados elegíveis.")
