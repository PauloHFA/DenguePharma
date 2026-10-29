package org.denguepharma.analysis;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.*;
import org.denguepharma.audit.AuditService;
import org.denguepharma.catalog.CatalogService.CatalogFilter;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

/** Snapshot de metadados coletados, separado dos valores cientificos aprovados. */
@Service
public class CorpusService {
    private final JdbcTemplate jdbc;
    private final ObjectMapper json;
    private final AnalysisService analyses;
    private final AuditService audit;
    public CorpusService(JdbcTemplate jdbc, ObjectMapper json, AnalysisService analyses, AuditService audit) {
        this.jdbc=jdbc; this.json=json; this.analyses=analyses; this.audit=audit;
    }

    public record Request(UUID protocolId, UUID previousAnalysisId) {}

    @Transactional(isolation=Isolation.REPEATABLE_READ)
    public Map<String,Object> create(Request request, UUID actor) {
        if (request.protocolId()==null) fail(HttpStatus.UNPROCESSABLE_ENTITY,"informe protocolId");
        var protocols=jdbc.queryForList("select id,code,version,title,question,cutoff_date,status,strategy::text as strategy,eligibility::text as eligibility from protocol where id=?", request.protocolId());
        if (protocols.isEmpty()) fail(HttpStatus.NOT_FOUND,"protocolo nao encontrado");
        var protocol=protocols.get(0);
        if ("DRAFT".equals(protocol.get("status"))) fail(HttpStatus.CONFLICT,"registre o protocolo");
        // Nunca copiar params de busca: podem conter credenciais de API.
        var sourceRuns=jdbc.queryForList("""
                select id,source,query,status,connector_version,api_version,records_seen,total_returned,
                    executed_at,finished_at from search_run where protocol_id=? order by executed_at,id
                """,request.protocolId());
        if (sourceRuns.isEmpty()) fail(HttpStatus.CONFLICT,"execute a coleta deste protocolo antes da analise");
        List<Map<String,Object>> documents=new ArrayList<>();
        Set<String> studyIds=new HashSet<>();
        for (var row:jdbc.queryForList("""
                select distinct on (d.id) d.id,d.doc_type,d.title,dv.id as version_id,dv.version_no,
                    dv.content_hash,dv.origin,dv.license,dv.access_status,dv.metadata::text as metadata,
                    dv.retrieved_at
                from search_run_document rd join search_run sr on sr.id=rd.search_run_id
                join document_version dv on dv.id=rd.document_version_id join document d on d.id=dv.document_id
                where sr.protocol_id=? and exists (
                    select 1 from study_document sd join study s on s.id=sd.study_id
                    where sd.document_id=d.id and not s.is_demo and s.status='ATIVO'
                      and (s.merged_into_id is null or exists(select 1 from study root where root.id=s.merged_into_id and root.status='ATIVO' and not root.is_demo)))
                order by d.id,dv.version_no desc
                """,request.protocolId())) {
            var item=new LinkedHashMap<String,Object>();
            item.put("documentId",row.get("id")); item.put("documentType",row.get("doc_type"));
            item.put("title",row.get("title")); item.put("versionId",row.get("version_id"));
            item.put("version",row.get("version_no")); item.put("contentHash",row.get("content_hash"));
            item.put("source",row.get("origin")); item.put("license",row.get("license"));
            item.put("accessStatus",row.get("access_status")); item.put("retrievedAt",row.get("retrieved_at"));
            var links=jdbc.queryForList("""
                    select distinct coalesce(s.merged_into_id,s.id) as study_id,sd.link_certainty,
                        root.screening_status,root.context,root.purpose
                    from study_document sd join study s on s.id=sd.study_id
                    join study root on root.id=coalesce(s.merged_into_id,s.id)
                    where sd.document_id=? and not root.is_demo and root.status='ATIVO'
                    order by study_id,sd.link_certainty
                    """,row.get("id"));
            item.put("studyLinks",links);
            for(var link:links) if("CONFIRMADO".equals(link.get("link_certainty"))) studyIds.add(link.get("study_id").toString());
            item.put("metadata",safeMetadata(read((String)row.get("metadata"))));
            documents.add(item);
        }
        var reviewed=analyses.reviewedStudies(new CatalogFilter(null,null,null,null,null,null)).stream()
                .filter(s->studyIds.contains(s.get("studyId").toString())).toList();
        UUID snapshot=UUID.randomUUID(),run=UUID.randomUUID(),event=UUID.randomUUID();
        var dataset=new LinkedHashMap<String,Object>();
        dataset.put("schemaVersion","3.0"); dataset.put("dictionaryVersion","corpus-v3.0");
        dataset.put("snapshotId",snapshot); dataset.put("createdAt",Instant.now().toString());
        JsonNode strategy=read((String)protocol.remove("strategy"));
        protocol.put("eligibility",read((String)protocol.get("eligibility")));
        protocol.put("maxRecordsPerSource",strategy.path("maxRecords").asInt(0));
        dataset.put("protocol",protocol); dataset.put("sourceRuns",sourceRuns);
        dataset.put("documents",documents); dataset.put("studies",reviewed); dataset.put("fields",AnalysisService.FIELDS);
        List<Map<String,Object>> scientificFields=new ArrayList<>();
        for(var study:reviewed) {
            scientificFields.addAll(jdbc.queryForList("""
                    select ef.id as field_id,ef.study_id,ef.field_name,ef.normalized_value as value,
                        ef.absence_status as status,dv.document_id,dv.id as document_version_id,
                        dv.content_hash,dv.origin as source,dv.license,es.locator
                    from extracted_field ef join extraction_run er on er.id=ef.extraction_run_id
                    join document_version dv on dv.id=er.document_version_id
                    left join evidence_span es on es.id=ef.evidence_span_id
                    where ef.study_id=? and ef.published and ef.review_status='APROVADO'
                      and ef.field_name in ('substance','substance_name','substance_published_name','population',
                        'comparator','limitations','design','phase','serotype','outcome','outcome_definition','outcome_category','sample_size')
                    order by ef.field_name,ef.id
                    """,study.get("studyId")));
        }
        dataset.put("scientificFields",scientificFields);
        dataset.put("chemicalMappings",jdbc.queryForList("""
                select distinct s.id as substance_id,s.published_name,s.normalized_name,a.alias,c.external_id as pubchem_cid
                from substance s join substance_alias c on c.substance_id=s.id and c.external_source='PUBCHEM_CID'
                left join substance_alias a on a.substance_id=s.id where not s.is_combination
                order by s.id,a.alias
                """));
        dataset.put("reviewedSchemaVersion","2.0"); dataset.put("reviewedDictionaryVersion",AnalysisService.DICTIONARY);
        if(request.previousAnalysisId()!=null) {
            JsonNode previous=read((String)analyses.input(request.previousAnalysisId()).get("content"));
            if(!"3.0".equals(previous.path("schemaVersion").asText())) fail(HttpStatus.UNPROCESSABLE_ENTITY,"comparacao exige snapshot de corpus v3");
            dataset.put("previous",Map.of("analysisId",request.previousAnalysisId(),"protocol",previous.path("protocol"),"documents",previous.path("documents")));
        }
        String content=write(dataset), hash=AnalysisService.sha256(content.getBytes(StandardCharsets.UTF_8));
        if(content.getBytes(StandardCharsets.UTF_8).length>8*1024*1024) fail(HttpStatus.UNPROCESSABLE_ENTITY,"snapshot excede 8 MiB; restrinja o protocolo");
        jdbc.update("insert into analysis_snapshot(id,requested_by,filters,dictionary_version,dataset,canonical_content,content_hash) values(?,?,?::jsonb,'corpus-v3.0',?::jsonb,?,?)",
                snapshot,actor,write(request),content,content,hash);
        jdbc.update("insert into outbox(event_id,aggregate_type,aggregate_id,event_type,payload) values(?,'analysis_run',?,'AnaliseSolicitada',?::jsonb)",event,run.toString(),write(Map.of("snapshotId",snapshot,"analysisId",run)));
        jdbc.update("insert into analysis_run(id,snapshot_id,source_event_id) values(?,?,?)",run,snapshot,event);
        audit.record(actor,"CORPUS_ANALYSIS_REQUESTED","analysis_run",run.toString(),null,write(Map.of("inputHash",hash,"documents",documents.size())),null);
        return analyses.get(run);
    }

    private ObjectNode safeMetadata(JsonNode raw) {
        ObjectNode safe=json.createObjectNode();
        for(String name:List.of("pmid","doi","pmcid","journal","pub_year","pubYear","language","publication_types","mesh","chemicals","registry_ids"))
            if(raw.has(name)) safe.set(name,raw.get(name));
        if(raw.has("hasResults")) safe.set("hasResults",raw.get("hasResults"));
        JsonNode section=raw.path("protocolSection");
        if(section.isObject()) {
            ObjectNode p=safe.putObject("protocolSection");
            copyFields(section,p,"identificationModule",List.of("nctId","briefTitle","officialTitle"));
            copyFields(section,p,"statusModule",List.of("overallStatus","startDateStruct","primaryCompletionDateStruct","completionDateStruct","studyFirstSubmitDate","studyFirstPostDateStruct","lastUpdatePostDateStruct","resultsFirstPostDateStruct"));
            copyFields(section,p,"designModule",List.of("studyType","phases","designInfo","enrollmentInfo"));
            copyFields(section,p,"conditionsModule",List.of("conditions","keywords"));
            ObjectNode arms=p.putObject("armsInterventionsModule");
            var interventions=arms.putArray("interventions");
            for(JsonNode intervention:section.path("armsInterventionsModule").path("interventions")) {
                ObjectNode i=json.createObjectNode();
                for(String name:List.of("type","name","otherNames")) if(intervention.has(name)) i.set(name,intervention.get(name));
                interventions.add(i);
            }
            var locations=p.putObject("contactsLocationsModule").putArray("locations");
            for(JsonNode location:section.path("contactsLocationsModule").path("locations"))
                if(location.hasNonNull("country")) locations.addObject().set("country",location.get("country"));
            var refs=p.putObject("referencesModule").putArray("references");
            for(JsonNode ref:section.path("referencesModule").path("references")) {
                ObjectNode r=json.createObjectNode();
                for(String name:List.of("pmid","type")) if(ref.has(name)) r.set(name,ref.get(name));
                refs.add(r);
            }
        }
        return safe;
    }
    private void copyFields(JsonNode section,ObjectNode target,String module,List<String> names) {
        ObjectNode out=target.putObject(module);
        for(String name:names) if(section.path(module).has(name)) out.set(name,section.path(module).get(name));
    }
    private JsonNode read(String content) { try { return content==null?json.createObjectNode():json.readTree(content); } catch(Exception e) { throw new IllegalStateException(e); } }
    private String write(Object value) { try { return json.writeValueAsString(value); } catch(Exception e) { throw new IllegalStateException(e); } }
    private void fail(HttpStatus status,String message) { throw new ResponseStatusException(status,message); }
}
