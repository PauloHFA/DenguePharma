"""Cobertura bibliografica por PMID, sem confirmar identidade de estudo ou resultados."""
from collections import defaultdict
import re
import pandas as pd
from ..domain import digest,json_bytes
from ..preparation.registries import groups

METHOD="registry-publication-reference-audit-1"
TYPES=("RESULT","DERIVED","BACKGROUND")
NOTICE="Referencias declaradas no snapshot, separadas pelo codigo da fonte. PMID coincidente gera candidato bibliografico, nao vinculo clinico confirmado. A cobertura mede identificadores: uma publicacao pode estar representada sem PMID. Referencia nao recuperada e ausencia de RESULT nao demonstram ausencia de publicacao, de resultado ou de evidencia. Nenhum artigo e buscado ou aprovado automaticamente."


def pmid(value):
    if value is None or isinstance(value,str) and not value.strip():return None,"NAO_INFORMADO"
    if not isinstance(value,str) or not re.fullmatch(r"[0-9]+",value.strip()):return None,"INVALIDO"
    normalized=value.strip().lstrip("0")
    return (normalized,"PRESENTE") if normalized else (None,"INVALIDO")


def reference(doc):
    return {k:doc.get(k) for k in ("documentId","versionId","version","contentHash","source","license","accessStatus")}


def analyze(snapshot):
    publications=defaultdict(dict);pub_identities={}
    for doc in snapshot.get("documents",[]):
        if doc.get("documentType")!="PUBLICACAO":continue
        identifier,_=pmid(doc.get("metadata",{}).get("pmid"));key=doc["documentId"]
        if key in pub_identities and pub_identities[key]!=identifier:raise ValueError("CONFLICTING_PUBLICATION_IDENTIFIER")
        pub_identities[key]=identifier
        if identifier:publications[identifier][(key,doc["versionId"],doc["contentHash"])]=reference(doc)
    registry=groups(snapshot);links={};types=set(TYPES)
    for trial,documents in sorted(registry.items()):
        for doc,nct,_ in documents:
            module=doc.get("metadata",{}).get("protocolSection",{}).get("referencesModule",{})
            if not isinstance(module,dict) or not isinstance(module.get("references",[]),list):raise ValueError("PUBLICATION_REFERENCE_METADATA_INVALID")
            for index,item in enumerate(module.get("references",[])):
                if not isinstance(item,dict) or item.get("type") is not None and not isinstance(item["type"],str):raise ValueError("PUBLICATION_REFERENCE_METADATA_INVALID")
                kind=(item.get("type") or "").strip().upper() or "NAO_INFORMADO";types.add(kind)
                identifier,state=pmid(item.get("pmid"))
                # Sem identificador valido nao se deduplicam citacoes por texto/titulo.
                key=(trial,kind,identifier) if identifier else (trial,kind,None,doc["documentId"],doc["versionId"],index)
                if key not in links:
                    matches=publications.get(identifier,{}) if identifier else {}
                    links[key]=dict(link_id=digest(json_bytes(key)),trial_id=trial,nct_id=nct,reference_type=kind,pmid=identifier,pmid_state=state,
                        status="CANDIDATO_NO_CORPUS" if matches else "NAO_RECUPERADO_NO_CORPUS" if identifier else "PMID_INVALIDO" if state=="INVALIDO" else "PMID_NAO_INFORMADO",
                        source_url="https://pubmed.ncbi.nlm.nih.gov/"+identifier+"/" if identifier else None,
                        publication_document_ids=sorted({r["documentId"] for r in matches.values()}),publication_references=[matches[k] for k in sorted(matches)],
                        trial_references=[],observations=[],automatically_confirmed=False)
                row=links[key];ref=reference(doc)
                if ref not in row["trial_references"]:row["trial_references"].append(ref)
                observation=dict(document_id=doc["documentId"],version_id=doc["versionId"],reference_index=index,reference_type=kind,pmid=identifier,pmid_state=state)
                if observation not in row["observations"]:row["observations"].append(observation)
    rows=sorted(links.values(),key=lambda r:r["link_id"]);coverage=[];missing=defaultdict(list)
    for row in rows:
        if row["status"]=="NAO_RECUPERADO_NO_CORPUS":missing[row["pmid"]].append(row)
    for kind in sorted(types):
        selected=[r for r in rows if r["reference_type"]==kind];ids={r["pmid"] for r in selected if r["pmid"]};matched=ids&set(publications)
        trials={r["trial_id"] for r in selected};valid_trials={r["trial_id"] for r in selected if r["pmid"]};candidate_trials={r["trial_id"] for r in selected if r["status"]=="CANDIDATO_NO_CORPUS"}
        coverage.append(dict(reference_type=kind,total_registry_units=len(registry),registry_units_with_references=len(trials),registry_units_with_valid_pmid=len(valid_trials),registry_units_with_candidate=len(candidate_trials),
            distinct_valid_pmids=len(ids),valid_pmids_in_corpus=len(matched),not_retrieved_pmids=len(ids-matched),missing_or_invalid_entries=sum(not r["pmid"] for r in selected),
            registry_reference_proportion=len(trials)/len(registry) if registry else None,pmid_coverage_proportion=len(matched)/len(ids) if ids else None))
    gaps=[]
    for identifier,items in sorted(missing.items()):
        refs={json_bytes(ref):ref for item in items for ref in item["trial_references"]}
        gaps.append(dict(pmid=identifier,source_url="https://pubmed.ncbi.nlm.nih.gov/"+identifier+"/",trial_ids=sorted({r["trial_id"] for r in items}),reference_types=sorted({r["reference_type"] for r in items}),
            trial_references=[refs[k] for k in sorted(refs)],status="NAO_RECUPERADO_NO_CORPUS"))
    summary=dict(method=METHOD,registry_units=len(registry),publication_documents=len(pub_identities),publications_with_distinct_pmid=len(publications),
        publication_documents_without_valid_pmid=sum(v is None for v in pub_identities.values()),coverage=coverage,missing_distinct_pmids=len(gaps),notice=NOTICE)
    return summary,dict(publication_reference_links=rows,publication_reference_coverage=coverage,publication_reference_missing=gaps)


def figures(summary,folder):
    frame=pd.DataFrame(summary["coverage"])
    if not len(frame) or not frame.distinct_valid_pmids.sum():return
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    folder.mkdir(parents=True,exist_ok=True)
    figure,axis=plt.subplots(figsize=(9,4))
    axis.bar(frame.reference_type,frame.valid_pmids_in_corpus,label="PMIDs no corpus — candidatos")
    axis.bar(frame.reference_type,frame.not_retrieved_pmids,bottom=frame.valid_pmids_in_corpus,label="PMIDs não recuperados")
    axis.set_title("Cobertura bibliográfica das referências declaradas")
    axis.set_ylabel("PMIDs distintos por tipo (tipos podem se sobrepor)")
    axis.legend();figure.tight_layout();figure.savefig(folder/"publication-refs-coverage.png",dpi=160);plt.close(figure)
