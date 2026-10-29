"""Diagnostico de metadados para calibracao. Nao decide elegibilidade nem beneficio."""
from collections import Counter
import re
from pathlib import Path

RULE_VERSION="metadata-calibration-1"
RULES={
    "VACINA":(r"\bvaccin\w*|\bimmunization\b","Menção a vacina"),
    "DESAFIO_CONTROLADO":(r"\bchallenge\b|\bhuman infection model\b","Menção a desafio/infecção humana controlada"),
    "VETORES":(r"\bwolbachia\b|\baedes\b|\blarvicid\w*|\bpupicid\w*","Menção a vetores"),
    "REVISAO":(r"\breview\b","Tipo ou título de revisão"),
    "DIAGNOSTICO":(r"\bscreening\b|\bdiagnostic\w*","Menção a rastreio/diagnóstico"),
    "PREVENCAO":(r"\bprevent\w*|\bprophyl\w*","Menção ou finalidade declarada de prevenção"),
}
NOTICE="Sinais automáticos de metadados, não revisados e não exclusivos. Não são decisões de inclusão/exclusão. Ausência de sinal não confirma elegibilidade. Resultados no registro não comprovam benefício clínico."


def analyze(snapshot,records):
    originals={d["documentId"]:d for d in snapshot["documents"]}
    screening={s["study_id"]:s["status"] for s in snapshot.get("clinical",{}).get("screening",[])}
    documents=[]; intervention_counts=Counter()
    for record in records:
        signals=[]; interventions={}
        for identifier in record["document_ids"]:
            doc=originals[identifier]; metadata=doc.get("metadata",{}); section=metadata.get("protocolSection",{})
            for field,value in (("title",doc.get("title","") or ""),("publication_types"," ".join(metadata.get("publication_types",[])))):
                for code,(pattern,_) in RULES.items():
                    match=re.search(pattern,value,re.I)
                    if match: signals.append(dict(code=code,document_id=identifier,field=field,token=match.group()))
            purpose=section.get("designModule",{}).get("designInfo",{}).get("primaryPurpose")
            if purpose=="PREVENTION": signals.append(dict(code="PREVENCAO",document_id=identifier,field="primaryPurpose",token="PREVENTION"))
            for intervention in section.get("armsInterventionsModule",{}).get("interventions",[]):
                kind=intervention.get("type") or "NAO_INFORMADO"; name=intervention.get("name") or "NAO_INFORMADO"
                interventions[(kind,name)]={"type":kind,"name":name}
                # Apenas a mencao literal a vacina; BIOLOGICAL por si so nao classifica vacina.
                match=re.search(RULES["VACINA"][0],name,re.I)
                if match: signals.append(dict(code="VACINA",document_id=identifier,field="intervention.name",token=match.group()))
        codes=sorted({s["code"] for s in signals})
        for kind in {kind for kind,_ in interventions}: intervention_counts[kind]+=1
        identifiers=record["identifiers"]
        pmid=next((v[5:] for v in identifiers if v.startswith("PMID:") and v[5:].isdigit()),None)
        nct=next((v[4:] for v in identifiers if v.startswith("NCT:") and re.fullmatch(r"NCT\d{8}",v[4:])),None)
        url="https://pubmed.ncbi.nlm.nih.gov/"+pmid+"/" if pmid else "https://clinicaltrials.gov/study/"+nct if nct else None
        documents.append({"document_id":record["document_id"],"study_id":record["study_id"],"document_type":record["document_type"],"title":record["title"],
            "sources":record["sources"],"identifiers":identifiers,"source_url":url,"signal_codes":codes,"signals":signals,"interventions":sorted(interventions.values(),key=lambda i:(i["type"],i["name"])),
            "signal_status":"SINAIS_METADATA_NAO_REVISADOS","review_status":screening.get(record["study_id"],"SEM_REVISAO_CLINICA"),"references":record["references"]})
    signals=[]
    for source in ["TODAS"]+sorted({s for d in documents for s in d["sources"]}):
        members=[d for d in documents if source=="TODAS" or source in d["sources"]]
        for code,(_,label) in RULES.items():
            count=sum(code in d["signal_codes"] for d in members)
            signals.append(dict(source=source,code=code,label=label,count=count,denominator=len(members),proportion=count/len(members) if members else None,overlapping=True))
    trials=sum(d["document_type"]=="REGISTRO_ENSAIO" for d in documents)
    types=[dict(intervention_type=kind,count=count,denominator=trials,proportion=count/trials if trials else None,overlapping=True) for kind,count in sorted(intervention_counts.items())]
    searches=[]
    for run in snapshot.get("sourceRuns",[]):
        source=run.get("source"); reported=run.get("total_returned")
        if type(reported) is not int or reported<0: reported=None
        retrieved=sum(source in d["sources"] for d in documents)
        searches.append(dict(source=source,query=run.get("query"),status=run.get("status"),reported_total=reported,retrieved_documents=retrieved,
            retrieved_fraction=retrieved/reported if reported and retrieved<=reported else None,executed_at=run.get("executed_at"),finished_at=run.get("finished_at")))
    summary=dict(rule_version=RULE_VERSION,documents=len(documents),documents_with_signals=sum(bool(d["signal_codes"]) for d in documents),
        documents_without_signals=sum(not d["signal_codes"] for d in documents),signals=[s for s in signals if s["source"]=="TODAS"],intervention_types=types,
        searches=searches,notice=NOTICE)
    return summary,{"calibration_documents":documents,"calibration_signals":signals,"calibration_intervention_types":types,"calibration_searches":searches}


def report(summary,input_hash):
    clinical=summary.get("clinical",{}); calibration=summary["calibration"]
    lines=["# Resultados gerais — diagnóstico do corpus", "", "**Resultados descritivos do snapshot; não constituem síntese de eficácia.**", "",
        f"Entrada: `{input_hash}`.", f"Corte registrado: {summary.get('protocol',{}).get('cutoff_date') or 'não informado'}.", "",
        "| Indicador | Resultado |", "|---|---:|",
        f"| Documentos deduplicados | {summary['documentCount']} |",f"| Publicações | {summary['publicationCount']} |",f"| Registros de ensaio | {summary['trialCount']} |",
        f"| Resultados clínicos revisados | {clinical.get('reviewed_results',0)} |", "", "## Registros de ensaio", ""]
    for item in summary["distributions"]:
        if item["field"] in {"design","recruitment","has_results"}:
            label={"design":"Desenho declarado","recruitment":"Situação declarada","has_results":"Resultados disponíveis no registro"}[item["field"]]
            lines.append(f"- {label} — {item['category']}: {item['count']}/{item['denominator']}.")
    lines += ["", "Disponibilidade de resultados não comprova benefício nem confirma elegibilidade. Os registros podem incluir vacinas, prevenção, desafio controlado ou outros contextos.","", "## Sinais para calibração", "",calibration["notice"],"", "| Sinal | Documentos / total |", "|---|---:|"]
    lines += [f"| {s['label']} | {s['count']}/{s['denominator']} |" for s in calibration["signals"]]
    lines += ["",f"Documentos com pelo menos um sinal: {calibration['documents_with_signals']}/{calibration['documents']}. Categorias se sobrepõem; não somar como exclusões.",
        "", "Tipos de intervenção são os declarados pelo registro. DRUG e BIOLOGICAL não são sinônimos de terapia elegível; OTHER não deve ser interpretado como substância farmacológica.","", "## Busca e limites", ""]
    for row in calibration["searches"]:
        lines.append(f"- {row['source']}: {row['retrieved_documents']} documentos no conjunto; total informado pela execução da busca: {row['reported_total'] if row['reported_total'] is not None else 'não informado'}.")
    lines += ["", "Os totais das buscas são históricos, amplos e específicos de cada fonte. Não somá-los como estudos únicos ou elegíveis. A fração recuperada não mede representatividade ou sensibilidade da busca.","", "## Conclusão permitida nesta etapa", ""]
    if not clinical.get("reviewed_results"):
        lines.append("Há material coletado para calibração, mas nenhum resultado clínico revisado. Não é possível apontar medicamentos benéficos, prejudiciais ou inconclusivos para pacientes com dengue com base nesta execução.")
    else:
        lines.append(f"Há {clinical['reviewed_results']} resultados revisados; consultar fichas e julgamentos humanos por desfecho/população. Este diagnóstico não atribui categorias clínicas.")
    lines += ["", "Próxima etapa: conferir referências sentinela, revisar o piloto de forma independente e calibrar a busca antes da coleta final. Zero campos revisados não significa ausência de efeito ou de estudos na literatura.",""]
    return "\n".join(lines)


def figures(calibration,folder: Path):
    if not calibration["documents"]: return
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt
    folder.mkdir(parents=True,exist_ok=True)
    rows=calibration["signals"]
    fig,ax=plt.subplots(figsize=(10,5))
    ax.barh([r["label"] for r in rows],[r["count"] for r in rows],color="#497e91")
    ax.set_xlabel(f"Documentos / {calibration['documents']} (categorias sobrepostas)")
    ax.set_title("Sinais de metadados para revisão — sem exclusão automática")
    fig.tight_layout(); fig.savefig(folder/"calibration-signals.png",dpi=150); plt.close(fig)
