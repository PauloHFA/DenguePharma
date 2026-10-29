"""Patrocinador responsavel declarado em registros coletados; sem julgamento clinico."""
import pandas as pd
from ..preparation.registries import groups as registry_groups,UNIT

MISSING="[NAO_INFORMADO]"
CONFLICT="[CONFLITO]"
NOTICE="Metadados dos registros coletados, com elegibilidade pendente. Patrocinador responsavel nao comprova financiamento, risco de vies ou eficacia. Nomes agrupados apenas por espacos e caixa, sem resolucao institucional."


def lead_sponsor(raw):
    if raw is None:return {}
    if not isinstance(raw,dict):raise ValueError("SPONSOR_METADATA_INVALID")
    result={}
    for key in ("name","class"):
        value=raw.get(key)
        if value is not None and not isinstance(value,str):raise ValueError("SPONSOR_METADATA_INVALID")
        if isinstance(value,str) and value.strip():result[key]=" ".join(value.split())
    return result


def analyze(snapshot):
    groups=registry_groups(snapshot,error_prefix="SPONSOR")
    identities={d["documentId"] for documents in groups.values() for d,_,_ in documents}
    rows=[]
    for key,documents in sorted(groups.items()):
        names=set();classes=set();references={};observations={}
        for doc,_,_ in documents:
            module=doc.get("metadata",{}).get("protocolSection",{}).get("sponsorCollaboratorsModule",{})
            if not isinstance(module,dict):raise ValueError("SPONSOR_METADATA_INVALID")
            sponsor=lead_sponsor(module.get("leadSponsor"))
            if sponsor.get("name"):names.add(sponsor["name"])
            if sponsor.get("class"):classes.add(sponsor["class"])
            reference={k:doc.get(k) for k in ("documentId","versionId","version","source","contentHash","license","accessStatus")}
            reference_key=(doc["documentId"],doc["versionId"],doc["contentHash"])
            observation=dict(document_id=doc["documentId"],version_id=doc["versionId"],sponsor_name=sponsor.get("name"),sponsor_type=sponsor.get("class"),
                sponsor_name_status="PRESENTE" if sponsor.get("name") else "NAO_INFORMADO",sponsor_type_status="PRESENTE" if sponsor.get("class") else "NAO_INFORMADO")
            if reference_key in observations and observations[reference_key]!=observation:raise ValueError("CONFLICTING_SPONSOR_REFERENCE")
            references[reference_key]=reference;observations[reference_key]=observation
        values={"sponsor_name":{n.casefold() for n in names},"sponsor_type":{c.upper() for c in classes}}
        row=dict(trial_id=key,nct_id=documents[0][1],identifier_status=documents[0][2],document_ids=sorted({d["documentId"] for d,_,_ in documents}),
            observed_names=sorted(names),observed_types=sorted(classes),references=[references[k] for k in sorted(references)],observations=[observations[k] for k in sorted(observations)])
        for field,distinct in values.items():
            row[field]=next(iter(distinct)) if len(distinct)==1 else None
            row[field+"_status"]="PRESENTE" if len(distinct)==1 else "CONFLITO" if distinct else "NAO_INFORMADO"
        rows.append(row)
    distributions=[];completeness=[]
    for field in ("sponsor_name","sponsor_type"):
        observations=[dict(status=r[field+"_status"],category=r[field] if r[field] is not None else CONFLICT if r[field+"_status"]=="CONFLITO" else MISSING) for r in rows]
        if observations:
            counts=pd.DataFrame(observations).groupby(["status","category"],dropna=False).size()
            for (status,category),count in counts.items():
                distributions.append(dict(field=field,status=status,category=category,count=int(count),denominator=len(rows),proportion=int(count)/len(rows),unit=UNIT))
        present=sum(r[field+"_status"]=="PRESENTE" for r in rows)
        completeness.append(dict(field=field,present=present,missing=sum(r[field+"_status"]=="NAO_INFORMADO" for r in rows),conflicts=sum(r[field+"_status"]=="CONFLITO" for r in rows),
            denominator=len(rows),proportion=present/len(rows) if rows else None,unit=UNIT))
    summary=dict(trials=len(rows),source_documents=len(identities),missing_nct=sum(r["identifier_status"]=="NAO_INFORMADO" for r in rows),invalid_nct=sum(r["identifier_status"]=="INVALIDO" for r in rows),
        distributions=distributions,completeness=completeness,notice=NOTICE)
    return summary,dict(corpus_sponsor_trials=rows,corpus_sponsor_distributions=distributions,corpus_sponsor_completeness=completeness)


def figures(summary,folder):
    rows=[r for r in summary["distributions"] if r["field"]=="sponsor_type"]
    if not rows:return
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    folder.mkdir(parents=True,exist_ok=True)
    figure,axis=plt.subplots(figsize=(8,4));axis.bar([r["category"] for r in rows],[r["count"] for r in rows])
    axis.set_title("Patrocinador responsável declarado — registros coletados")
    axis.set_ylabel("Registros (NCT ou documento)")
    for i,row in enumerate(rows):axis.text(i,row["count"],f"{row['count']}/{row['denominator']}",ha="center",va="bottom")
    axis.set_ylim(0,max(r["count"] for r in rows)*1.25);figure.tight_layout()
    figure.savefig(folder/"sponsors-types.png",dpi=160);plt.close(figure)
