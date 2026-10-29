package org.denguepharma;

import static org.assertj.core.api.Assertions.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.TimeUnit;
import org.denguepharma.analysis.*;
import org.denguepharma.pipeline.PipelineService;
import org.denguepharma.user.Role;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

class CorpusIntegrationTest extends AbstractIntegrationTest {
    @Autowired CorpusService corpus;
    @Autowired AnalysisService analyses;
    @Autowired PipelineService pipeline;

    @Test void corpusEIsoladoPorProtocoloExcluiDemoRetraidosESegredosEPreservaSnapshot() throws Exception {
        UUID protocol=protocol();
        addDocument(protocol,false,false,"123");
        addDocument(protocol,true,false,"456");
        addDocument(protocol,false,true,"789");
        addDocument(protocol(),false,false,"987");
        var run=corpus.create(new CorpusService.Request(protocol,null),null);
        String content=(String)analyses.input((UUID)run.get("id")).get("content");
        var snapshot=json.readTree(content);
        assertThat(snapshot.path("documents").size()).isOne();
        assertThat(snapshot.path("studies").size()).isZero();
        assertThat(snapshot.path("sourceRuns").size()).isEqualTo(3);
        assertThat(content).doesNotContain("FULLTEXT_SECRET","CONTACT_SECRET","API_KEY_SECRET");
        assertThat(snapshot.path("documents").get(0).path("metadata").path("pmid").asText()).isEqualTo("123");
        addDocument(protocol,false,false,"999");
        assertThat(analyses.input((UUID)run.get("id")).get("content")).isEqualTo(content);
    }

    @Test void publicacaoExigePapelConclusaoEVersaoSeguraEArtefatosSaoPublicosApenasDepois() throws Exception {
        UUID protocol=protocol(); addDocument(protocol,false,false,"123");
        UUID id=(UUID)corpus.create(new CorpusService.Request(protocol,null),null).get("id");
        mvc.perform(get("/api/public/analyses")).andExpect(status().isOk()).andExpect(content().json("[]"));
        mvc.perform(get("/api/public/analyses/"+id)).andExpect(status().isNotFound());
        mvc.perform(get("/api/public/analyses/"+id+"/artifacts").param("name","dataset.json")).andExpect(status().isNotFound());
        mvc.perform(post("/api/analyses/"+id+"/publish")).andExpect(status().isUnauthorized());
        mvc.perform(post("/api/analyses/"+id+"/publish").header("Authorization",tokenFor(Role.LEITOR))).andExpect(status().isForbidden());
        mvc.perform(post("/api/analyses/"+id+"/publish").header("Authorization",tokenFor(Role.PESQUISADOR))).andExpect(status().isConflict());
        // Executa exatamente o comando publico de analise, valida o ZIP no backend e conclui pelo lease.
        String python=System.getenv().getOrDefault("PIPELINE_PYTHON",Path.of("..","workers",".venv","Scripts","python.exe").toAbsolutePath().toString());
        Path folder=Files.createTempDirectory(Path.of("target"),"corpus-test-");
        Path input=folder.resolve("input.json"); Files.writeString(input,(String)analyses.input(id).get("content"),StandardCharsets.UTF_8);
        var process=new ProcessBuilder(python,"-m","denguepharma_workers.analysis","--input",input.toAbsolutePath().toString(),"--output",folder.resolve("output").toAbsolutePath().toString())
                .redirectErrorStream(true).redirectOutput(folder.resolve("python.log").toFile()).start();
        assertThat(process.waitFor(90,TimeUnit.SECONDS)).isTrue();
        assertThat(process.exitValue()).withFailMessage("%s",Files.readString(folder.resolve("python.log"))).isZero();
        UUID event=jdbc.queryForObject("select source_event_id from analysis_run where id=?",UUID.class,id);
        var claim=pipeline.claimDelivery(event);
        pipeline.completeAnalysis((UUID)claim.get("jobId"),(UUID)claim.get("leaseToken"),Files.readAllBytes(folder.resolve("output/bundle.zip")));
        mvc.perform(post("/api/analyses/"+id+"/publish").header("Authorization",tokenFor(Role.PESQUISADOR))).andExpect(status().isOk());
        mvc.perform(post("/api/analyses/"+id+"/publish").header("Authorization",tokenFor(Role.PESQUISADOR))).andExpect(status().isOk());
        mvc.perform(get("/api/public/analyses")).andExpect(status().isOk()).andExpect(jsonPath("$[0].id").value(id.toString()));
        mvc.perform(get("/api/public/analyses/"+id+"/artifacts").param("name","summary.json"))
            .andExpect(status().isOk()).andExpect(jsonPath("$.documentCount").value(1)).andExpect(jsonPath("$.studyCount").value(0));
        mvc.perform(get("/api/public/analyses/"+id+"/artifacts").param("name","bundle.zip")).andExpect(status().isOk()).andExpect(content().contentType("application/zip"));
        mvc.perform(post("/api/public/analyses/"+id)).andExpect(status().isUnauthorized());
        mvc.perform(get("/api/imports")).andExpect(status().isUnauthorized());
        assertThat(jdbc.queryForObject("select count(*) from analysis_publication",Integer.class)).isOne();
    }

    @Test void camposCientificosAdicionaisExigemAprovacaoEConservamProvenienciaSemTrechos() throws Exception {
        UUID protocol=protocol(),study=addDocument(protocol,false,false,"123");
        jdbc.update("update study set context='HUMANO',purpose='TRATAMENTO',screening_status='INCLUIDO_NUCLEO' where id=?",study);
        UUID version=jdbc.queryForObject("select dv.id from document_version dv join study_document sd on sd.document_id=dv.document_id where sd.study_id=?",UUID.class,study);
        UUID extraction=jdbc.queryForObject("""
                insert into extraction_run(document_version_id,pipeline_version,model_provider,model_version,prompt_hash,schema_version,status)
                values(?,'fixture','MANUAL','fixture','hash','1','COMPLETED') returning id
                """,UUID.class,version);
        UUID span=jdbc.queryForObject("insert into evidence_span(document_version_id,locator,text) values(?,'fixture:1','FULLTEXT_SECRET') returning id",UUID.class,version);
        jdbc.update("""
                insert into extracted_field(extraction_run_id,study_id,field_name,normalized_value,evidence_span_id,review_status,published)
                values(?,?,'population','Adultos',?,'APROVADO',true)
                """,extraction,study,span);
        jdbc.update("""
                insert into extracted_field(extraction_run_id,study_id,field_name,normalized_value,evidence_span_id)
                values(?,?,'limitations','PRIVATE_DRAFT',?)
                """,extraction,study,span);
        UUID run=(UUID)corpus.create(new CorpusService.Request(protocol,null),null).get("id");
        String content=(String)analyses.input(run).get("content");
        var snapshot=json.readTree(content);
        assertThat(snapshot.path("studies").size()).isOne();
        assertThat(snapshot.path("scientificFields").size()).isOne();
        assertThat(snapshot.path("scientificFields").get(0).path("value").asText()).isEqualTo("Adultos");
        assertThat(snapshot.path("scientificFields").get(0).path("document_version_id").asText()).isEqualTo(version.toString());
        assertThat(content).doesNotContain("FULLTEXT_SECRET","PRIVATE_DRAFT");
    }

    private UUID protocol() {
        return jdbc.queryForObject("""
                insert into protocol(code,version,title,question,sources,strategy,eligibility,cutoff_date,status)
                values(?,1,'Corpus','Pergunta','["PUBMED"]','{"maxRecords":25}','{}','2026-10-27','REGISTERED') returning id
                """,UUID.class,UUID.randomUUID().toString());
    }
    private UUID addDocument(UUID protocol,boolean demo,boolean retracted,String pmid) {
        UUID study=jdbc.queryForObject("insert into study(title,is_demo,status,retraction_reason) values('Fixture',?,?,?) returning id",UUID.class,demo,retracted?"RETRATADO":"ATIVO",retracted?"Teste":null);
        UUID doc=jdbc.queryForObject("insert into document(doc_type,title) values('PUBLICACAO','Fixture') returning id",UUID.class);
        String metadata="{\"pmid\":\""+pmid+"\",\"pub_year\":\"2020\",\"abstract\":\"FULLTEXT_SECRET\",\"contacts\":\"CONTACT_SECRET\"}";
        UUID version=jdbc.queryForObject("insert into document_version(document_id,version_no,content_hash,origin,retrieved_at,metadata) values(?,1,?,'PUBMED',now(),?::jsonb) returning id",UUID.class,doc,AnalysisService.sha256(metadata.getBytes(StandardCharsets.UTF_8)),metadata);
        jdbc.update("insert into study_document(study_id,document_id,report_role,link_certainty) values(?,?,'PUBLICACAO_PRINCIPAL','CONFIRMADO')",study,doc);
        UUID run=jdbc.queryForObject("insert into search_run(protocol_id,source,query,connector_version,status,params) values(?,'PUBMED','dengue','test','COMPLETED','{\"api_key\":\"API_KEY_SECRET\"}') returning id",UUID.class,protocol);
        jdbc.update("insert into search_run_document(search_run_id,document_version_id) values(?,?)",run,version);
        return study;
    }
}
