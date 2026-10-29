package org.denguepharma;

import static org.assertj.core.api.Assertions.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
import com.fasterxml.jackson.databind.JsonNode;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.denguepharma.analysis.AnalysisService;
import org.denguepharma.catalog.CatalogService.CatalogFilter;
import org.denguepharma.pipeline.PipelineService;
import org.denguepharma.user.Role;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.DataAccessException;
import org.springframework.web.server.ResponseStatusException;

class AnalysisIntegrationTest extends AbstractIntegrationTest {
    @Autowired AnalysisService analyses;
    @Autowired PipelineService pipeline;
    private CatalogFilter all() { return new CatalogFilter(null,null,null,null,null,null); }

    @Test
    void snapshotSoUsaValoresAprovadosPreservaConflitosEExcluiDadosNaoElegiveis() throws Exception {
        UUID included=study("Incluido");
        field(included,"design","RCT",true);
        field(included,"design","RCT",true); // Outro relato nao duplica estudo nem cria conflito.
        field(included,"phase","2",true); field(included,"phase","3",true);
        field(included,"substance","Nao revisada",false);
        UUID demo=study("Demo"); field(demo,"design","RCT",true); jdbc.update("update study set is_demo=true where id=?",demo);
        UUID excluded=study("Excluido"); field(excluded,"design","RCT",true); jdbc.update("update study set screening_status='EXCLUIDO' where id=?",excluded);
        UUID retracted=study("Retratado"); field(retracted,"design","RCT",true); jdbc.update("update study set status='RETRATADO',retraction_reason='Teste' where id=?",retracted);
        UUID merged=study("Absorvido"); field(merged,"design","RCT",true); jdbc.update("update study set merged_into_id=? where id=?",included,merged);
        UUID draft=study("Rascunho"); field(draft,"design","RCT",false);
        jdbc.update("insert into reassessment_task(study_id,trigger_type) values(?,'FONTE_ALTERADA')",included);
        var run=analyses.create(all(),null);
        JsonNode dataset=json.readTree((String) analyses.input((UUID)run.get("id")).get("content"));
        assertThat(dataset.path("studies").size()).isOne();
        var row=dataset.path("studies").get(0);
        assertThat(row.path("fields").path("design").path("value").asText()).isEqualTo("RCT");
        assertThat(row.path("fields").path("phase").path("status").asText()).isEqualTo("CONFLITO");
        assertThat(row.path("fields").path("substance").path("status").asText()).isEqualTo("SEM_REVISAO");
        assertThat(row.path("reassessmentPending").asBoolean()).isTrue();
        assertThat(dataset.toString()).doesNotContain("RESUMO_NAO_REVISADO","FULLTEXT_SECRET","Nao revisada","quotedText","evidence_text");
        field(included,"serotype","DENV-2",true);
        jdbc.update("update study set status='RETRATADO', retraction_reason='Retirada posterior' where id=?",included);
        assertThat(analyses.input((UUID)run.get("id")).get("content")).isEqualTo(dataset.toString());
    }

    @Test
    void filtrosUsamValoresRevisadosEEstadosDeAusenciaPersistem() throws Exception {
        UUID study=study("Filtros"); field(study,"design","COORTE",true);
        absence(study,"phase","NAO_APLICAVEL"); absence(study,"serotype","NAO_INFORMADO");
        var run=analyses.create(new CatalogFilter(null,null,null,"COORTE",null,null),null);
        var dataset=json.readTree((String)analyses.input((UUID)run.get("id")).get("content"));
        assertThat(dataset.path("studies").size()).isOne();
        assertThat(dataset.path("studies").get(0).path("fields").path("phase").path("status").asText()).isEqualTo("NAO_APLICAVEL");
        var empty=analyses.create(new CatalogFilter(null,null,null,"RESUMO_NAO_REVISADO",null,null),null);
        assertThat(empty.get("study_count")).isEqualTo(0);
    }

    @Test
    void permissoesDaApiEIntegridadeImutavel() throws Exception {
        mvc.perform(post("/api/analyses").contentType("application/json").content("{}")) .andExpect(status().isUnauthorized());
        mvc.perform(post("/api/analyses").header("Authorization",tokenFor(Role.LEITOR)).contentType("application/json").content("{}")) .andExpect(status().isForbidden());
        String response=mvc.perform(post("/api/analyses").header("Authorization",tokenFor(Role.PESQUISADOR)).contentType("application/json").content("{}"))
                .andExpect(status().isAccepted()).andExpect(jsonPath("$.status").value("PENDING")).andReturn().getResponse().getContentAsString();
        UUID id=UUID.fromString(json.readTree(response).path("id").asText());
        mvc.perform(get("/api/analyses/"+id).header("Authorization",tokenFor(Role.LEITOR))).andExpect(status().isOk());
        mvc.perform(get("/api/analyses/"+id+"/artifacts").param("name","bundle.zip").header("Authorization",tokenFor(Role.LEITOR))).andExpect(status().isNotFound());
        mvc.perform(get("/api/analyses/"+id+"/artifacts").param("name","dataset.json").header("Authorization",tokenFor(Role.LEITOR)))
                .andExpect(status().isOk()).andExpect(jsonPath("$.schemaVersion").value("2.0"));
        mvc.perform(get("/api/analyses").header("Authorization",tokenFor(Role.LEITOR))).andExpect(status().isOk());
        assertThatThrownBy(()->jdbc.update("update analysis_snapshot set content_hash='alterado' where id=(select snapshot_id from analysis_run where id=?)",id)).isInstanceOf(DataAccessException.class);
        assertThatThrownBy(()->jdbc.update("delete from analysis_run where id=?",id)).isInstanceOf(DataAccessException.class);
    }

    @Test
    void jobDeAnaliseProtegidoPorLeaseEFalhaNaoPublicaArtefatos() {
        var run=analyses.create(all(),null);
        UUID id=(UUID)run.get("id");
        UUID event=jdbc.queryForObject("select source_event_id from analysis_run where id=?",UUID.class,id);
        var claim=pipeline.claimDelivery(event);
        UUID job=(UUID)claim.get("jobId"), lease=(UUID)claim.get("leaseToken");
        assertThat(claim.get("jobType")).isEqualTo("ANALYZE_EVIDENCE");
        assertThat(pipeline.input(job,lease).get("content_hash")).isEqualTo(run.get("input_hash"));
        assertThatThrownBy(()->pipeline.completeAnalysis(job,UUID.randomUUID(),new byte[]{1})).isInstanceOf(ResponseStatusException.class);
        assertThatThrownBy(()->pipeline.completeAnalysis(job,lease,new byte[]{1})).isInstanceOf(ResponseStatusException.class);
        assertThat(jdbc.queryForObject("select count(*) from analysis_artifact",Integer.class)).isZero();
        assertThat(pipeline.fail(job,lease,"ANALYSIS_FAILED").get("status")).isEqualTo("PENDING");
        assertThat(analyses.get(id).get("status")).isEqualTo("PENDING");
    }

    private UUID study(String title) {
        return jdbc.queryForObject("""
                insert into study(title,context,purpose,screening_status,design,phase,effect_summary)
                values(?,'HUMANO','TRATAMENTO','INCLUIDO_NUCLEO','RESUMO_NAO_REVISADO','RESUMO_NAO_REVISADO','FULLTEXT_SECRET') returning id
                """,UUID.class,title);
    }
    private void absence(UUID study,String field,String status) { insert(study,field,null,status,true); }
    private void field(UUID study,String field,String value,boolean published) { insert(study,field,value,"PRESENTE",published); }
    private void insert(UUID study,String field,String value,String status,boolean published) {
        UUID doc=jdbc.queryForObject("insert into document(doc_type,title) values('PUBLICACAO','Fixture') returning id",UUID.class);
        String hash=AnalysisService.sha256(UUID.randomUUID().toString().getBytes(java.nio.charset.StandardCharsets.UTF_8));
        UUID version=jdbc.queryForObject("""
                insert into document_version(document_id,version_no,content_hash,origin,access_status,retrieved_at,metadata)
                values(?,1,?,'PUBMED','SOMENTE_RESUMO',now(),'{"abstract":"FULLTEXT_SECRET"}') returning id
                """,UUID.class,doc,hash);
        jdbc.update("insert into study_document(study_id,document_id,report_role,link_certainty) values(?,?,'PUBLICACAO_PRINCIPAL','CONFIRMADO')",study,doc);
        UUID extraction=jdbc.queryForObject("""
                insert into extraction_run(document_version_id,pipeline_version,model_provider,model_version,prompt_hash,schema_version)
                values(?,'fixture','MANUAL','manual-v1','fixture','1') returning id
                """,UUID.class,version);
        UUID span="PRESENTE".equals(status) ? jdbc.queryForObject("insert into evidence_span(document_version_id,locator,text) values(?,'char:0-3','FULLTEXT_SECRET') returning id",UUID.class,version) : null;
        jdbc.update("""
                insert into extracted_field(extraction_run_id,study_id,field_name,normalized_value,absence_status,evidence_span_id,review_status,published)
                values(?,?,?,?,?,?,?,?)
                """,extraction,study,field,value,status,span,published?"APROVADO":"RASCUNHO_IA",published);
    }
}
