"""Formulario de triagem sem sugestoes preselecionadas nem votos alheios."""
from typing import get_args
import streamlit as st
from .. import client
from .models import Classification,Screen
from .refresh import rerun_curation

LABELS={"established_dengue":"Pacientes com dengue estabelecida?","context":"Contexto do estudo","population":"População","severity":"Gravidade","disease_phase":"Fase da doença","purpose":"Finalidade","design":"Desenho","pharmacological_intervention":"Intervenção farmacológica?"}
DEFAULTS={"established_dengue":"INCERTO","context":"INCERTO","population":"INCERTO","severity":"NAO_INFORMADA","disease_phase":"NAO_INFORMADA","purpose":"OUTRO","design":"INCERTO","pharmacological_intervention":"INCERTO"}


def payload(row,decision,classification,reason,*,adjudicate=False):
    data=Screen.model_validate(dict(study_id=row["study_id"],basis_hash=row["basis_hash"],decision=decision,classification=classification,reason=reason)).model_dump()
    if adjudicate:
        if not row.get("adjudication"): raise ValueError("Conflito atual e papel de adjudicador são necessários")
        data["votes_hash"]=row["adjudication"]["votes_hash"]
    return data


def render(state,key,token):
    with st.expander("Triagem por campos — revisão humana",expanded=True):
        from .personal_review import visible_rows,LABELS as PERSONAL_LABELS
        notice_key="screen_notice_"+key
        if notice_key in st.session_state:st.success(st.session_state.pop(notice_key))
        rows=state["queue"]
        if not rows: st.info("Sem estudos nesta fila."); return
        mode=st.selectbox("Mostrar na minha fila",["Minha revisão pendente","Minha revisão registrada","Conflitos para adjudicação","Toda a fila"],key="screen_filter_"+key)
        rows=visible_rows(rows,mode)
        if not rows:
            st.info("Nenhuma identidade neste filtro. A ausência de tarefa pessoal não conclui a seleção independente nem aprova calibração.");return
        ids={r["study_id"]:r for r in rows}
        study=st.selectbox("Estudo a revisar",list(ids),format_func=lambda i:(ids[i].get("title") or i)+" · "+PERSONAL_LABELS.get(ids[i].get("personal_review",{}).get("status"),"Revisão humana"),key="screen_study_"+key)
        row=ids[study]
        from .dossier_ui import render as documentary_context
        documentary_context(key,token,row)
        st.write("Documentos vinculados:",row["document_ids"])
        st.caption("Consulte a fonte permitida antes de decidir. Nenhum sinal de metadados preenche estes campos. Sua própria decisão anterior pode ser recuperada; votos alheios permanecem protegidos.")
        st.code(row["basis_hash"],language=None)
        can_adjudicate=row.get("can_adjudicate_screening",bool(row.get("adjudication")) and not row.get("own_decision"))
        adjudicate=st.checkbox("Adjudicar conflito atual",key="adjudicate_"+key+study,disabled=not can_adjudicate) and can_adjudicate
        if adjudicate: st.json(row["adjudication"])
        if not row.get("personal_review",{}).get("can_review",True) and not adjudicate:
            st.info("Duas outras pessoas já ocuparam as vagas de revisão. Nenhum novo voto será registrado por esta conta. Para adjudicar, é necessário conflito atual, papel autorizado e conferência explícita.");return
        own=row.get("own_decision") or {}; values=own.get("classification",{})
        with st.form("screen_fields_"+key+study+str(adjudicate)):
            classification={}
            for field,label in LABELS.items():
                options=list(get_args(Classification.model_fields[field].annotation))
                selected=values.get(field,DEFAULTS[field])
                classification[field]=st.selectbox(label,options,index=options.index(selected))
            interventions=st.text_area("Intervenções farmacológicas — uma por linha",value="\n".join(values.get("interventions",[])))
            decisions=["INCERTO","INCLUIR","EXCLUIR"]
            decision=st.selectbox("Decisão humana",decisions,index=decisions.index(own.get("decision","INCERTO")))
            reason=st.text_area("Justificativa e material consultado",value=own.get("reason",""))
            if st.form_submit_button("Salvar triagem humana"):
                classification["interventions"]=[line.strip() for line in interventions.splitlines() if line.strip()]
                data=payload(row,decision,classification,reason,adjudicate=adjudicate)
                kind="SCREEN_ADJUDICATED" if adjudicate else "SCREENED"
                client.private(f"/{key}/actions/{kind}",token=token,data=data)
                st.session_state[notice_key]="Decisão registrada. A fila foi atualizada; a seleção independente e a calibração continuam separadas."
                rerun_curation()
