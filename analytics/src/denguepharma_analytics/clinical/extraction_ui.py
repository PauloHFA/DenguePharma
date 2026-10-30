"""Extracao por campos, sem preencher numeros cientificos ausentes."""
import math
import re
from copy import deepcopy
from typing import get_args

from pydantic import ValidationError
import streamlit as st
from .. import client
from .models import Result
from .refresh import rerun_curation

ABSENCES=["NAO_EXTRAIDO","NAO_INFORMADO","NAO_APLICAVEL","INCERTO","NAO_HOUVE_EVENTO"]
REFERENCE_FIELDS=["intervention","comparator","population","severity","disease_phase","intervention_timing","analysis_population","outcome_definition","timepoint","unit","support_care","risk_of_bias","treatment.n","treatment.n_randomized","treatment.events","treatment.mean","treatment.sd","control.n","control.n_randomized","control.events","control.mean","control.sd","reported.estimate","reported.ci_low","reported.ci_high","reported.confidence_level"]


def numeric(value,*,integer=False):
    value=value.strip()
    if not value: return None
    if integer:
        if not re.fullmatch(r"-?\d+",value): raise ValueError("Contagens devem ser números inteiros, sem separador de milhar.")
        return int(value)
    if "," in value and "." in value: raise ValueError("Use vírgula ou ponto decimal, sem separador de milhar.")
    number=float(value.replace(",","."))
    if not math.isfinite(number): raise ValueError("Valores numéricos devem ser finitos.")
    return number


def occurrences(text,quote,limit=100):
    if not quote: return []
    starts=[]; offset=0
    while len(starts)<limit:
        found=text.find(quote,offset)
        if found<0: break
        starts.append(found);offset=found+1
    return starts


def options(field): return list(get_args(Result.model_fields[field].annotation))


def build_payload(raw,domains=""):
    data=deepcopy(raw)
    for arm in ("treatment","control"):
        for field,value in data[arm].items():
            if field!="arm_id" and isinstance(value,str): data[arm][field]=numeric(value,integer=field in {"n","n_randomized","events"})
    if data.get("reported"):
        for field,value in data["reported"].items():
            if field!="measure" and isinstance(value,str): data["reported"][field]=numeric(value)
    domain_map={}
    for line in domains.splitlines():
        if line.strip():
            name,separator,reason=line.partition("=")
            if not separator or not name.strip() or not reason.strip(): raise ValueError("Use domínio=justificativa para cada domínio avaliado.")
            if name.strip() in domain_map: raise ValueError("Domínio metodológico repetido.")
            domain_map[name.strip()]=reason.strip()
    data["risk_of_bias_domains"]=domain_map
    return Result.model_validate(data).model_dump()


def references(key,token,study,sources):
    session_key="extraction_refs_"+key+study["study_id"]
    if session_key not in st.session_state: st.session_state[session_key]=[]
    with st.expander("Trechos de suporte deste rascunho"):
        versions=[s for s in sources if s["document_id"] in study["document_ids"]]
        if versions:
            version=st.selectbox("Fonte do trecho",[v["version_id"] for v in versions],key="extraction_source_"+key+study["study_id"])
            if st.checkbox("Consultar fonte e adicionar trecho",key="extraction_open_"+key+study["study_id"]):
                source=client.private(f"/{key}/sources/{version}",token=token)
                st.text(source["text"])
                field=st.selectbox("Campo sustentado",REFERENCE_FIELDS,key="extraction_field_"+key+study["study_id"])
                quote=st.text_area("Trecho literal, preservando espaços",key="extraction_quote_"+key+study["study_id"])
                starts=occurrences(source["text"],quote)
                start=st.selectbox("Ocorrência conferida na fonte",[None]+starts,format_func=lambda p:"Selecione explicitamente" if p is None else f"Caracteres {p} a {p+len(quote)}",key="extraction_occurrence_"+key+study["study_id"])
                st.caption("Até 100 ocorrências. Se houver mais, selecione trecho mais específico ou use o gerador de localizadores. Nenhum trecho é escolhido automaticamente.")
                if st.button("Adicionar suporte ao rascunho",key="extraction_add_"+key+study["study_id"]):
                    if start is None: st.error("Escolha uma ocorrência literal da fonte.")
                    else:
                        ref=client.private(f"/{key}/locators",token=token,data=dict(version_id=version,field=field,start=start,end=start+len(quote)))["reference"]
                        if ref not in st.session_state[session_key]: st.session_state[session_key].append(ref)
        st.dataframe(st.session_state[session_key],hide_index=True,width="stretch")
        if st.button("Limpar trechos deste rascunho",key="extraction_clear_"+key+study["study_id"]): st.session_state[session_key]=[];rerun_curation()
        st.caption("Referências ficam nesta sessão privada até serem salvas no rascunho. Sua presença literal não valida o significado clínico.")
    return list(st.session_state[session_key])


def number_field(label,key,absence_states,field,*,integer=False):
    value=st.text_input(label,key=key,help="Inteiro sem separador de milhar; vazio preserva ausência." if integer else "Valor decimal, sem separador de milhar; vazio preserva ausência.")
    absence=st.selectbox("Se ausente — "+label,ABSENCES,key=key+"_absence")
    if not value.strip(): absence_states[field]=absence
    return value


def draft_form(flow,state,key,token):
    studies={s["study_id"]:s for s in flow["included_studies"]}
    if not studies:
        st.info("Extração bloqueada: nenhum estudo foi incluído pela seleção independente atual. Conclua a triagem; nenhum resultado será criado automaticamente.");return
    study=studies[st.selectbox("Estudo incluído para extração",list(studies),format_func=lambda i:studies[i].get("title") or i,key="extraction_study_"+key)]
    c=study["classification"]; refs=references(key,token,study,state["sources"])
    kind=st.selectbox("Como registrar o efeito",["REPORTED","RR","MD"],key="extraction_kind_"+key+study["study_id"])
    st.caption("Valores começam vazios. REPORTED preserva a estimativa publicada; RR e MD só calculam efeitos em braços paralelos randomizados independentes. Não use p-valor como conclusão.")
    with st.form("extraction_form_"+key+study["study_id"]+kind):
        data=dict(study_id=study["study_id"],basis_hash=study["basis_hash"],effect_type=kind,evidence=refs)
        data["comparison_id"]=st.text_input("Identificador estável da comparação")
        data["intervention"]=st.selectbox("Intervenção incluída na triagem",c["interventions"])
        data["comparator"]=st.text_input("Comparador")
        for field,label in (("population","População do resultado"),("severity","Gravidade do resultado"),("disease_phase","Fase da doença do resultado")):
            values=options(field); data[field]=st.selectbox(label,values,index=values.index(c[field]))
        data["purpose"]=c["purpose"];data["design"]=c["design"]
        st.caption("Finalidade e desenho consolidados: "+c["purpose"]+" / "+c["design"]+". Subgrupos de população mista exigem suporte específico.")
        for field,label in (("intervention_timing","Momento de início da intervenção"),("analysis_population","População de análise (ITT, PP ou outra)"),("outcome_definition","Definição do desfecho"),("timepoint","Período de avaliação"),("unit","Unidade do resultado")):
            data[field]=st.text_input(label)
        data["outcome_code"]=st.selectbox("Desfecho do protocolo",list(flow["outcomes"]),format_func=lambda v:flow["outcomes"][v]+" · "+v)
        data["direction"]=st.selectbox("Direção favorável do desfecho",["NAO_DEFINIDA","MENOR_MELHOR","MAIOR_MELHOR"])
        data["independent_arms"]=st.checkbox("Conferi que os braços são independentes para esta comparação.")
        absence_states={}
        for arm,label in (("treatment","Intervenção"),("control","Comparador")):
            st.write("**Braço — "+label+"**")
            values=dict(arm_id=st.text_input("Identificador do braço — "+label))
            fields=[("n","Participantes analisados",True),("n_randomized","Participantes randomizados",True)]
            if kind=="RR": fields.append(("events","Participantes com evento",True))
            if kind=="MD": fields.extend([("mean","Média",False),("sd","Desvio padrão",False)])
            for name,title,integer in fields:
                field=arm+"."+name
                values[name]=number_field(title+" — "+label,"extraction_num_"+key+study["study_id"]+kind+field,absence_states,field,integer=integer)
            data[arm]=values
        if kind=="REPORTED":
            reported=dict(measure=st.selectbox("Medida publicada",["RR","OR","HR","MD"]))
            for name,title in (("estimate","Estimativa publicada"),("ci_low","Limite inferior do intervalo"),("ci_high","Limite superior do intervalo"),("confidence_level","Nível de confiança (ex.: 0,95)")):
                reported[name]=number_field(title,"extraction_reported_"+key+study["study_id"]+name,absence_states,"reported."+name)
            data["reported"]=reported
        data["support_care"]=st.text_area("Cuidados de suporte e cointervenções")
        data["limitations"]=st.text_area("Limitações e informações não disponíveis")
        data["risk_of_bias"]=st.selectbox("Avaliação metodológica",["NAO_AVALIADO","BAIXO","ALGUMAS_PREOCUPACOES","ALTO"])
        data["risk_of_bias_reason"]=st.text_area("Justificativa da avaliação metodológica")
        data["risk_of_bias_instrument"]=st.text_input("Instrumento utilizado (quando avaliado)") or None
        domains=st.text_area("Domínios avaliados — uma linha domínio=justificativa")
        data["absence_states"]=absence_states
        corrections=[r for r in flow["candidates"] if r["data"]["study_id"]==study["study_id"]]
        correction=st.selectbox("Corrigir resultado anterior (opcional)",[None]+[r["id"] for r in corrections],format_func=lambda v:v or "Novo resultado")
        data["supersedes"]=correction;data["correction_reason"]=st.text_input("Motivo da correção (se houver)") or None
        check=st.form_submit_button("Conferir rascunho sem salvar")
        save=st.form_submit_button("Salvar rascunho para revisão independente")
        if check or save:
            try:
                validated=build_payload(data,domains)
                if check:
                    value=client.private(f"/{key}/results/preview",token=token,data=validated)
                    st.json(value);st.caption("Prévia somente de leitura. Intervalo e presença de trechos não definem benefício.")
                    if value.get('changes'):
                        from .result_changes_ui import render as show_changes
                        show_changes(value['changes'])
                else:
                    value=client.private(f"/{key}/actions/RESULT_DRAFTED",token=token,data=validated)
                    st.success("Rascunho registrado; ainda não aprovado nem publicado.");st.json(value)
            except ValidationError as error:
                for item in error.errors(): st.error(".".join(str(p) for p in item["loc"])+": "+item["msg"])
            except ValueError as error: st.error(str(error))


def decisions(flow,key,token):
    if not flow["candidates"]: st.info("Nenhum rascunho clínico registrado.");return
    cards={r["id"]:r for r in flow["candidates"]}
    selected=st.selectbox("Resultado a conferir",list(cards),format_func=lambda i:cards[i]["data"]["intervention"]+" / "+cards[i]["data"]["outcome_code"]+" / "+cards[i]["stage"]+" / "+i[:8],key="extraction_decision_"+key)
    card=cards[selected];st.write("Estado: **"+card["stage"]+"**");st.json(card["data"]);st.json(card["effect"])
    if card['data'].get('supersedes'):
        with st.expander('Alterações desta correção'):
            changes=client.private(f'/{key}/results/{selected}/changes',token=token)
            from .result_changes_ui import render as show_changes
            if not changes['current_basis']:st.warning('Base desatualizada: a comparação é histórica e não autoriza aprovação.')
            show_changes(changes)
    st.caption("Conferir braços, denominadores, unidades, população, tempo e fontes. A API exige identidades independentes e suporte literal antes da aprovação final.")
    reopen=True
    if card["stage"] in {"APROVADO","CONFLITO","ADJUDICACAO_REJEITADA","REVISAO_REJEITADA"}:
        reopen=st.checkbox("Registrar reavaliação deste resultado, preservando o histórico.",key="extraction_reopen_"+key+selected)
    for action,label,permission in (("RESULT_REVIEWED","Revisão independente",card["can_review"]),("RESULT_ADJUDICATED","Adjudicação",card["can_adjudicate"])):
        with st.form("extraction_decision_form_"+key+selected+action):
            decision=st.selectbox(label,[None,"ACEITAR","REJEITAR"],format_func=lambda v:v or "Escolha uma decisão humana")
            reason=st.text_area("Justificativa — "+label)
            if st.form_submit_button("Registrar "+label.lower(),disabled=not (permission and reopen)):
                if decision is None or len(reason.strip())<5: st.error("Selecione a decisão e justifique a conferência.")
                else:
                    value=client.private(f"/{key}/actions/{action}",token=token,data=dict(result_id=selected,decision=decision,reason=reason))
                    st.success("Decisão registrada. Atualize a fila; publicação exige nova execução explícita.");st.json(value)
    if not card["can_review"]: st.info("Sua identidade não pode revisar este resultado próprio, substituído ou com base desatualizada.")


def render(state,key,token):
    flow=client.private(f"/{key}/extraction",token=token)
    with st.expander("Extração clínica por campos"):
        draft_form(flow,state,key,token)
    with st.expander("Revisão e adjudicação dos resultados"):
        decisions(flow,key,token)
