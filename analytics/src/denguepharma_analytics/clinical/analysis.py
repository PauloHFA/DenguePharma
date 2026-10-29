"""Tabelas e figuras por estudo; nenhuma combinacao estatistica ou classificacao automatica."""
import json
from collections import Counter
from pathlib import Path

from ..domain import digest, json_bytes
from .models import scope_for, result_set_hash

NOTICE="Sem meta-analise, ranking ou recomendacao terapeutica. Ausencia de resultado revisado nao significa ausencia de beneficio. Categorias clinicas dependem de julgamento humano documentado."


def validate(block):
    if block.get("schema_version")!="clinical-evidence-1" or digest(json_bytes(block["protocol"]))!=block["protocol_hash"]: raise ValueError("CLINICAL_PROTOCOL_HASH")
    if block["protocol"]["analysis"]["pooling"]: raise ValueError("META_ANALYSIS_OUT_OF_SCOPE")
    notices=block.get("document_integrity",[])
    if not isinstance(notices,list):raise ValueError("INVALID_INTEGRITY_NOTICES")
    required={"event_id","study_id","document_id","version_id","content_hash","status","category","source_reference"}
    document_ids=set();blocked_studies=set();blocked_documents=set()
    for notice in notices:
        if not isinstance(notice,dict) or set(notice)!=required or any(not isinstance(v,str) or not v.strip() for v in notice.values()):raise ValueError("INVALID_INTEGRITY_NOTICE")
        if notice["document_id"] in document_ids or notice["status"] not in {"EM_REAVALIACAO","RETIRADO","REGULARIZADO"} or notice["category"] not in {"RETRATACAO","CORRECAO_RELEVANTE","OUTRO_ALERTA_DOCUMENTAL"}:raise ValueError("INVALID_INTEGRITY_NOTICE")
        document_ids.add(notice["document_id"])
        if notice["status"] in {"EM_REAVALIACAO","RETIRADO"}:
            blocked_studies.add(notice["study_id"]);blocked_documents.add(notice["document_id"])
    ids=set()
    for row in block["results"]:
        if row["study_id"] in blocked_studies or any(ref.get("document_id") in blocked_documents for ref in row.get("references",[])):raise ValueError("BLOCKED_CLINICAL_REFERENCE")
        if row["result_id"] in ids or not row.get("decision_id") or not row.get("references"): raise ValueError("CLINICAL_RESULT_PROVENANCE")
        ids.add(row["result_id"])
        if "evidence" in row or any("quote" in ref for ref in row["references"]): raise ValueError("PRIVATE_CLINICAL_TEXT")
        for ref in row["references"]:
            if not all(ref.get(k) for k in ("version_id","text_hash","document_id","content_hash","field")): raise ValueError("INCOMPLETE_CLINICAL_REFERENCE")
    for group in block["groups"]:
        members=[r for r in block["results"] if scope_for(r)==group["scope"]]
        if not members or set(group["result_ids"])!={r["result_id"] for r in members}: raise ValueError("INCOMPLETE_SYNTHESIS_MEMBERS")
        signature=result_set_hash(members)
        if signature!=group["result_set_hash"]: raise ValueError("CLINICAL_SYNTHESIS_HASH")


def datasets(block):
    if not block:
        return {"clinical_screening":[],"clinical_results":[],"clinical_synthesis":[],"clinical_references":[],"clinical_conflicts":[],"clinical_absences":[]}
    validate(block)
    references=[{"result_id":r["result_id"],**ref} for r in block["results"] for ref in r["references"]]
    results=[]
    for row in block["results"]:
        results.append({**row,"treatment_n":row["treatment"]["n"],"control_n":row["control"]["n"],
            "participants_comparison":row["treatment"]["n"]+row["control"]["n"] if row["independent_arms"] and row["treatment"]["n"] and row["control"]["n"] else None})
    return {"clinical_screening":block["screening"],"clinical_results":results,"clinical_synthesis":block["groups"],
        "clinical_references":references,"clinical_conflicts":block["conflicts"],"clinical_absences":block["absences"]}


def summary(block):
    tables=datasets(block)
    return {"available":bool(block),"status":"RESULTADOS_REVISADOS" if tables["clinical_results"] else "SEM_RESULTADOS_CLINICOS_REVISADOS",
        **({"document_integrity":{"statuses":dict(Counter(r["status"] for r in block["document_integrity"])),
            "blocked_documents":sum(r["status"] in {"EM_REAVALIACAO","RETIRADO"} for r in block["document_integrity"]),
            "notice":"Alertas humanos registrados neste snapshot; sem deteccao automatica ou atualizacao de execucoes historicas."}}
            if block and "document_integrity" in block else {}),
        "screening_counts":dict(Counter(r["status"] for r in tables["clinical_screening"])),"reviewed_results":len(tables["clinical_results"]),
        "included_studies":len({r["study_id"] for r in tables["clinical_screening"] if r["status"]=="INCLUIR"}),
        "reviewed_studies":len({r["study_id"] for r in tables["clinical_results"]}),"synthesis_groups":len(tables["clinical_synthesis"]),
        "conflicts":len(tables["clinical_conflicts"]),"protocol_hash":block["protocol_hash"] if block else None,"notice":NOTICE}


def figures(block, folder: Path):
    if not block or not block["results"]: return
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt
    folder.mkdir(parents=True,exist_ok=True)
    for group in block["groups"]:
        members=sorted([r for r in block["results"] if r["result_id"] in group["result_ids"]],key=lambda r:(r["study_id"],r["comparison_id"]))
        valid=[r for r in members if r["estimate"] is not None and r["ci_low"] is not None and r["ci_high"] is not None]
        if not valid: continue
        fig,ax=plt.subplots(figsize=(10,max(3,len(valid)*.6+2)))
        for i,row in enumerate(valid):
            ax.plot([row["ci_low"],row["ci_high"]],[i,i],color="#287070")
            ax.plot(row["estimate"],i,"s",color="#174c4c")
        ratio=group["scope"]["measure"] in {"RR","OR","HR"}
        if ratio: ax.set_xscale("log")
        ax.axvline(1 if ratio else 0,color="grey",linestyle="--")
        ax.set_yticks(range(len(valid)),[r["study_id"][:18]+" / "+r["comparison_id"][:16] for r in valid])
        ax.set_xlabel(group["scope"]["measure"]+"; IC individual (nivel registrado na ficha)")
        ax.set_title(group["scope"]["intervention"]+" vs "+group["scope"]["comparator"]+"\n"+group["scope"]["population"]+" / "+group["scope"]["outcome_code"]+" / "+group["scope"]["timepoint"])
        fig.text(.5,.01,f"Sem efeito combinado. {len(valid)}/{len(members)} resultados com IC. Comparacoes podem compartilhar participantes.",ha="center",fontsize=8)
        fig.tight_layout(rect=(0,.06,1,1)); fig.savefig(folder/(group["scope_id"]+".png"),dpi=150); plt.close(fig)
