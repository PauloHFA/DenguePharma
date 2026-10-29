"""Auditoria descritiva de datas declaradas. Nao estima sobrevivencia ou efeito clinico."""
from datetime import date
import json
import re
import pandas as pd
from ..domain import json_bytes
from ..preparation.registries import groups,UNIT

METHOD="registry-reporting-audit-1"
NOTICE="Disponibilidade e datas declaradas nos registros coletados, com elegibilidade pendente. Indicadores refletem a versao armazenada, sem reconstituir o estado historico no corte. Intervalos sao dias de calendario entre campos do registro, nao sobrevida de pacientes. Sem censura, Kaplan-Meier, meta-analise ou inferencia de eficacia. Deposito no registro e publicacao vinculada sao eventos distintos."
RESULT_STATES=("DISPONIVEL","NAO_DECLARADO_DISPONIVEL","NAO_INFORMADO","CONFLITO")


def parse_date(raw):
    value=raw.strip() if isinstance(raw,str) else None
    if raw is None or value=="":return dict(raw=value,precision="AUSENTE",value=None)
    try:
        if value and re.fullmatch(r"\d{4}-\d{2}-\d{2}",value):return dict(raw=value,precision="DIA",value=date.fromisoformat(value))
        if value and re.fullmatch(r"\d{4}-\d{2}",value):date.fromisoformat(value+"-01");return dict(raw=value,precision="MES",value=None)
        if value and re.fullmatch(r"\d{4}",value):date.fromisoformat(value+"-01-01");return dict(raw=value,precision="ANO",value=None)
    except ValueError:pass
    return dict(raw=value,precision="INVALIDA",value=None)


def date_struct(raw):
    if raw is None:return None
    if not isinstance(raw,dict):raise ValueError("REPORTING_METADATA_INVALID")
    if any(raw.get(k) is not None and not isinstance(raw[k],str) for k in ("date","type")):raise ValueError("REPORTING_METADATA_INVALID")
    value={k:raw[k].strip().upper() if k=="type" else raw[k].strip() for k in ("date","type") if raw.get(k) is not None}
    return value if any(value.values()) else None


def choose(observations,field):
    values={json_bytes(o[field]):o[field] for o in observations if o.get(field) is not None}
    return (next(iter(values.values())),"PRESENTE") if len(values)==1 else (None,"CONFLITO" if values else "NAO_INFORMADO")


def analyze(snapshot):
    cutoff=parse_date((snapshot.get("protocol") or {}).get("cutoff_date"));rows=[]
    for key,documents in sorted(groups(snapshot).items()):
        observations=[];refs={}
        for doc,_,_ in documents:
            metadata=doc.get("metadata",{});module=metadata.get("protocolSection",{}).get("statusModule",{})
            if not isinstance(module,dict):raise ValueError("REPORTING_METADATA_INVALID")
            has=metadata.get("hasResults");status=module.get("overallStatus")
            if has is not None and type(has) is not bool or status is not None and not isinstance(status,str):raise ValueError("REPORTING_METADATA_INVALID")
            observations.append(dict(document_id=doc["documentId"],version_id=doc["versionId"],has_results=has,
                overall_status=status.strip().upper() or None if isinstance(status,str) else None,
                primary=date_struct(module.get("primaryCompletionDateStruct")),results=date_struct(module.get("resultsFirstPostDateStruct")),last_update=date_struct(module.get("lastUpdatePostDateStruct"))))
            ref={k:doc.get(k) for k in ("documentId","versionId","version","contentHash","source","license","accessStatus")}
            refs[(doc["documentId"],doc["versionId"],doc["contentHash"])]=ref
        row=dict(trial_id=key,nct_id=documents[0][1],cutoff_date=cutoff["raw"],references=[refs[k] for k in sorted(refs)],observations=observations,interval_days=None)
        for field in ("has_results","overall_status"):
            row[field],row[field+"_state"]=choose(observations,field)
        dates={}
        for field in ("primary","results","last_update"):
            value,state=choose(observations,field);parsed=parse_date((value or {}).get("date"));dates[field]=parsed["value"]
            if state=="CONFLITO":parsed["precision"]="CONFLITO"
            row.update({field+"_date":parsed["raw"],field+"_precision":parsed["precision"],field+"_type":(value or {}).get("type"),field+"_state":state})
        flags=[]
        if any(row[f+"_state"]=="CONFLITO" for f in ("has_results","overall_status","primary","results","last_update")):flags.append("METADADOS_EM_CONFLITO")
        if row["overall_status"]!="COMPLETED":flags.append("STATUS_NAO_DECLARADO_COMPLETED")
        if row["has_results"] is not True:flags.append("INDICADOR_EM_CONFLITO" if row["has_results_state"]=="CONFLITO" else "INDICADOR_NAO_INFORMADO" if row["has_results"] is None else "SEM_RESULTADOS_INDICADOS")
        if row["has_results"] is False and row["results_date"]:flags.append("INDICADOR_E_DATA_DIVERGENTES")
        if cutoff["precision"]!="DIA":flags.append("CORTE_INVALIDO_OU_AUSENTE")
        for field in ("primary","results","last_update"):
            if row[field+"_precision"]!="DIA":flags.append(field.upper()+"_SEM_DATA_DIARIA")
            if row[field+"_type"]!="ACTUAL":flags.append(field.upper()+"_TIPO_NAO_ACTUAL")
            if dates[field] and cutoff["value"] and dates[field]>cutoff["value"]:flags.append(field.upper()+"_APOS_CORTE")
        if dates["primary"] and dates["results"] and dates["results"]<dates["primary"]:flags.append("RELATO_ANTES_CONCLUSAO_PRIMARIA")
        row["flags"]=flags;row["interval_status"]="CALCULAVEL" if not flags else "CONFERENCIA_NECESSARIA"
        if not flags:row["interval_days"]=(dates["results"]-dates["primary"]).days
        row["result_category"]="CONFLITO" if row["has_results_state"]=="CONFLITO" else "NAO_INFORMADO" if row["has_results"] is None else "DISPONIVEL" if row["has_results"] else "NAO_DECLARADO_DISPONIVEL"
        rows.append(row)
    availability=[]
    for field in ("result_category","overall_status","primary_precision","results_precision","last_update_precision","interval_status"):
        values=pd.Series(["[CONFLITO]" if field=="overall_status" and r["overall_status_state"]=="CONFLITO" else r[field] or "[NAO_INFORMADO]" for r in rows],dtype="object")
        for category,count in values.value_counts(dropna=False).sort_index().items():availability.append(dict(field=field,category=category,count=int(count),denominator=len(rows),proportion=int(count)/len(rows),unit=UNIT))
    crossed=[]
    if rows:
        frame=pd.DataFrame(rows);frame["completion"]=frame.overall_status.fillna("[NAO_INFORMADO]")
        frame.loc[frame.overall_status_state=="CONFLITO","completion"]="[CONFLITO]"
        frame["result"]=pd.Categorical(frame.result_category,categories=RESULT_STATES)
        table=pd.crosstab(frame.completion,frame.result,dropna=False)
        for status in table.index:
            denominator=int(table.loc[status].sum())
            for category in RESULT_STATES:
                count=int(table.loc[status,category]);crossed.append(dict(overall_status=status,result_category=category,count=count,denominator=denominator,proportion=count/denominator if denominator else None,unit=UNIT))
    days=pd.Series([r["interval_days"] for r in rows if r["interval_days"] is not None],dtype="float64")
    stats=dict(origin="primaryCompletionDateStruct.date",endpoint="resultsFirstPostDateStruct.date",observed=len(days),completed=sum(r["overall_status"]=="COMPLETED" for r in rows),total_trials=len(rows),unit="dias_de_calendario",censoring=False,
        min=int(days.min()) if len(days) else None,max=int(days.max()) if len(days) else None,median=float(days.median()) if len(days) else None,q1=float(days.quantile(.25)) if len(days) else None,q3=float(days.quantile(.75)) if len(days) else None)
    summary=dict(method=METHOD,cutoff=cutoff["raw"],trials=len(rows),availability=availability,interval_summary=stats,notice=NOTICE)
    return summary,dict(reporting_registry=rows,reporting_availability=availability,reporting_intervals=[stats],reporting_results_by_status=crossed)


def figures(summary,folder):
    values=summary["interval_summary"]
    if not values["observed"]:return
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    folder.mkdir(parents=True,exist_ok=True)
    figure,axis=plt.subplots(figsize=(8,4))
    axis.errorbar([values["median"]],[0],xerr=[[values["median"]-values["q1"]],[values["q3"]-values["median"]]],fmt="o",capsize=8)
    axis.set_yticks([0],[f"{values['observed']} pares válidos"]);axis.set_xlabel("Dias de calendário: mediana e intervalo interquartil (sem IC)")
    axis.set_title("Conclusão primária → primeiro depósito declarado")
    figure.tight_layout();figure.savefig(folder/"reporting-intervals.png",dpi=160);plt.close(figure)
