"""Snapshot de metadados via PostgreSQL somente leitura, sem limite HTTP de 8 MiB."""
from datetime import datetime,timezone
import json
from uuid import UUID,uuid4
from ..domain import digest,json_bytes
from .postgres import connect_read_only
from .snapshot import load_snapshot
from ..analyses.sponsors import lead_sponsor


def safe_metadata(raw):
    safe={k:raw[k] for k in ("pmid","doi","pmcid","journal","pub_year","pubYear","language","publication_types","mesh","chemicals","registry_ids","hasResults") if k in raw}
    section=raw.get("protocolSection")
    if isinstance(section,dict):
        definitions={"identificationModule":["nctId","briefTitle","officialTitle"],"statusModule":["overallStatus","startDateStruct","primaryCompletionDateStruct","completionDateStruct","studyFirstSubmitDate","studyFirstPostDateStruct","lastUpdatePostDateStruct","resultsFirstPostDateStruct"],"designModule":["studyType","phases","designInfo","enrollmentInfo"],"conditionsModule":["conditions","keywords"]}
        result={module:{k:section.get(module,{}).get(k) for k in fields if k in section.get(module,{})} for module,fields in definitions.items()}
        result["armsInterventionsModule"]={"interventions":[{k:i[k] for k in ("type","name","otherNames") if k in i} for i in section.get("armsInterventionsModule",{}).get("interventions",[])]}
        result["contactsLocationsModule"]={"locations":[dict(country=i["country"]) for i in section.get("contactsLocationsModule",{}).get("locations",[]) if i.get("country")]}
        result["referencesModule"]={"references":[{k:i[k] for k in ("pmid","type") if k in i} for i in section.get("referencesModule",{}).get("references",[])]}
        if "sponsorCollaboratorsModule" in section:
            module=section["sponsorCollaboratorsModule"]
            if not isinstance(module,dict):raise ValueError("SPONSOR_METADATA_INVALID")
            result["sponsorCollaboratorsModule"]={"leadSponsor":lead_sponsor(module.get("leadSponsor"))}
        safe["protocolSection"]=result
    return safe


def snapshot_from_runs(protocol_id,run_ids):
    protocol_id=UUID(str(protocol_id)); ids=[UUID(str(i)) for i in run_ids]
    if not ids or len(set(ids))!=len(ids):raise ValueError("INVALID_COLLECTION_RUN_IDS")
    with connect_read_only() as db:
        db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        protocol=db.execute("SELECT id,code,version,title,cutoff_date,status,strategy::text AS strategy FROM protocol WHERE id=%s",(protocol_id,)).fetchone()
        if not protocol or protocol["status"]=="DRAFT":raise ValueError("REGISTERED_PROTOCOL_REQUIRED")
        runs=db.execute("SELECT id,protocol_id,source,query,status,connector_version,api_version,records_seen,total_returned,executed_at,finished_at FROM search_run WHERE id=ANY(%s) ORDER BY source,id",(ids,)).fetchall()
        if len(runs)!=len(ids) or any(r["protocol_id"]!=protocol_id or r["status"]!="COMPLETED" for r in runs):raise ValueError("COMPLETED_COLLECTION_RUNS_REQUIRED")
        if len({r["source"] for r in runs})!=len(runs):raise ValueError("AMBIGUOUS_COLLECTION_SOURCE_RUNS")
        links={}
        for row in db.execute("""SELECT DISTINCT dv.document_id,coalesce(s.merged_into_id,s.id) AS study_id,sd.link_certainty,root.screening_status,root.context,root.purpose
            FROM search_run_document rd JOIN document_version dv ON dv.id=rd.document_version_id
            JOIN study_document sd ON sd.document_id=dv.document_id JOIN study s ON s.id=sd.study_id
            JOIN study root ON root.id=coalesce(s.merged_into_id,s.id)
            WHERE rd.search_run_id=ANY(%s) AND NOT s.is_demo AND s.status='ATIVO' AND NOT root.is_demo AND root.status='ATIVO'
            ORDER BY dv.document_id,study_id,sd.link_certainty""",(ids,)):
            links.setdefault(str(row["document_id"]),[]).append({k:str(v) if isinstance(v,UUID) else v for k,v in row.items() if k!="document_id"})
        documents=[]
        with db.cursor(name="clinical_collection_documents") as cursor:
            cursor.execute("""SELECT DISTINCT ON (d.id) d.id,d.doc_type,d.title,dv.id AS version_id,dv.version_no,dv.content_hash,dv.origin,dv.license,dv.access_status,dv.retrieved_at,dv.canonical_content
                FROM search_run_document rd JOIN document_version dv ON dv.id=rd.document_version_id JOIN document d ON d.id=dv.document_id
                WHERE rd.search_run_id=ANY(%s) ORDER BY d.id,dv.version_no DESC""",(ids,))
            for row in cursor:
                doc_id=str(row["id"])
                if doc_id not in links:continue
                if digest(row["canonical_content"].encode())!=row["content_hash"]:raise ValueError("DOCUMENT_VERSION_HASH_MISMATCH")
                raw=json.loads(row["canonical_content"]); metadata=safe_metadata(raw)
                identity=raw.get("protocolSection",{}).get("identificationModule",{})
                title=raw.get("title") or identity.get("briefTitle") or identity.get("officialTitle") or row["title"]
                documents.append(dict(documentId=doc_id,versionId=str(row["version_id"]),version=row["version_no"],documentType=row["doc_type"],title=title,source=row["origin"],contentHash=row["content_hash"],license=row["license"],accessStatus=row["access_status"],retrievedAt=row["retrieved_at"].isoformat(),metadata=metadata,studyLinks=links[doc_id]))
        source_runs=[{k:str(v) if isinstance(v,UUID) else v.isoformat() if isinstance(v,datetime) else v for k,v in r.items() if k!="protocol_id"} for r in runs]
        data=dict(schemaVersion="3.0",dictionaryVersion="corpus-v3.0",snapshotId=str(uuid4()),createdAt=datetime.now(timezone.utc).isoformat(),
            protocol=dict(id=str(protocol_id),code=protocol["code"],version=protocol["version"],title=protocol["title"],cutoff_date=protocol["cutoff_date"].isoformat(),maxRecordsPerSource=json.loads(protocol["strategy"]).get("maxRecords",0)),
            sourceRuns=source_runs,documents=documents,studies=[],scientificFields=[],collectionNotice="Metadados coletados; nenhuma aprovacao clinica transferida. Vinculos e anotacoes legadas sao referencias historicas, nao triagem independente deste novo corpus.")
        return load_snapshot(json_bytes(data),origin=dict(type="postgres_collection_read_only",protocol_id=str(protocol_id),run_ids=sorted(str(i) for i in ids),metadata_only=True))
