package org.denguepharma;

import static org.assertj.core.api.Assertions.assertThat;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.time.Duration;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.TimeUnit;
import org.denguepharma.catalog.CatalogService.CatalogFilter;
import org.denguepharma.ops.ReportAndOpsService;
import org.denguepharma.analysis.AnalysisService;
import org.denguepharma.extraction.ExtractionService;
import org.denguepharma.extraction.ExtractionService.ReviewInput;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.containers.wait.strategy.Wait;

/** Teste opcional com servidor HTTP, RabbitMQ, MinIO e processo Python reais, em recursos isolados. */
@EnabledIfEnvironmentVariable(named = "PIPELINE_INTEGRATION", matches = "true")
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
        properties = "denguepharma.pipeline.token=pipeline-e2e-token-at-least-32-characters")
class PipelineEndToEndIntegrationTest extends AbstractIntegrationTest {
    @LocalServerPort int port;
    @Autowired ReportAndOpsService reports;
    @Autowired AnalysisService analyses;
    @Autowired org.denguepharma.analysis.CorpusService corpus;
    @Autowired ExtractionService extractions;

    @Test
    void documentoFilaWorkerArquivosERelatorioSemDuplicacao() throws Exception {
        try (var rabbit = new GenericContainer<>("rabbitmq:3.13-management-alpine")
                    .withEnv("RABBITMQ_DEFAULT_USER", "pipeline").withEnv("RABBITMQ_DEFAULT_PASS", "pipeline-test-password")
                    .withExposedPorts(5672).waitingFor(Wait.forLogMessage(".*Server startup complete.*", 1)).withStartupTimeout(Duration.ofMinutes(3));
             var minio = new GenericContainer<>(System.getenv().getOrDefault("PIPELINE_MINIO_IMAGE", "denguepharma-minio:local"))
                    .withEnv("MINIO_ROOT_USER", "pipeline").withEnv("MINIO_ROOT_PASSWORD", "pipeline-test-password")
                    .withCommand("server", "/data").withExposedPorts(9000)
                    .waitingFor(Wait.forHttp("/minio/health/ready").forPort(9000)).withStartupTimeout(Duration.ofMinutes(3))) {
            rabbit.start(); minio.start();
            String content = "{\"abstract\":\"We randomized 50 adult patients with DENV-2.\",\"license\":\"CC-BY\"}";
            String hash = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(content.getBytes(StandardCharsets.UTF_8)));
            UUID study = jdbc.queryForObject("insert into study(title) values('E2E isolated fixture') returning id", UUID.class);
            UUID doc = jdbc.queryForObject("insert into document(doc_type,title) values('PUBLICACAO','E2E fixture') returning id", UUID.class);
            UUID version = jdbc.queryForObject("""
                    insert into document_version(document_id,version_no,content_hash,origin,storage_uri,access_status,retrieved_at,metadata,canonical_content)
                    values(?,1,?,'PUBMED',?,'SOMENTE_RESUMO',now(),?::jsonb,?) returning id
                    """, UUID.class, doc, hash, "s3://denguepharma-corpus/pubmed/" + hash + ".json", content, content);
            jdbc.update("insert into study_document(study_id,document_id,report_role,link_certainty) values(?,?,'PUBLICACAO_PRINCIPAL','CONFIRMADO')", study, doc);
            UUID event = UUID.randomUUID();
            jdbc.update("insert into outbox(event_id,aggregate_type,aggregate_id,event_type,payload) values(?,'document_version',?,'DocumentoImportado','{}')", event, version.toString());
            runPython(rabbit, minio, "-m", "denguepharma_workers.runtime", "--once");
            assertThat(jdbc.queryForObject("select count(*) from document_archive", Integer.class)).isOne();
            assertThat(jdbc.queryForObject("select count(*) from extraction_run", Integer.class)).isOne();
            assertThat(jdbc.queryForObject("select count(*) from extracted_field", Integer.class)).isEqualTo(2);
            assertThat(jdbc.queryForObject("select count(*) from extracted_field where published", Integer.class)).isZero();
            assertThat(jdbc.queryForObject("select status from job where source_event_id = ?", String.class, event)).isEqualTo("COMPLETED");
            // Forca reentrega real no broker, sem recriar evento/job/extracao.
            runPython(rabbit, minio, "-c", """
                    import json
                    from denguepharma_workers.runtime import Settings, Worker, QUEUE
                    w=Worker(Settings.from_env()); w.connect()
                    w.channel.basic_publish('', QUEUE, json.dumps({'eventId':'%s','schemaVersion':1}).encode(), mandatory=True)
                    w.consume_one(); w.close()
                    """.formatted(event));
            assertThat(jdbc.queryForObject("select count(*) from extraction_run", Integer.class)).isOne();
            UUID snapshot = (UUID) reports.createSnapshot(new CatalogFilter(null,null,null,null,null,null), null).get("id");
            runPython(rabbit, minio, "-m", "denguepharma_workers.runtime", "--once");
            assertThat(jdbc.queryForObject("select count(*) from report_artifact where report_snapshot_id = ?", Integer.class, snapshot)).isEqualTo(3);
            // A analise recebe somente dados aprovados, nunca os rascunhos que o worker acabou de criar.
            UUID serotype = jdbc.queryForObject("select id from extracted_field where field_name='serotype'", UUID.class);
            UUID adjudicator = users.findByEmailIgnoreCase("adjudicador@test.org").orElseThrow().getId();
            extractions.reviewField(new ReviewInput(serotype,"ACEITAR",null,null,null,null,true,true), adjudicator, true);
            jdbc.update("update study set screening_status='INCLUIDO_NUCLEO',context='HUMANO',purpose='TRATAMENTO' where id=?",study);
            UUID analysis = (UUID) analyses.create(new CatalogFilter(null,null,null,null,null,null),null).get("id");
            runPython(rabbit,minio,"-m","denguepharma_workers.runtime","--once");
            assertThat(analyses.get(analysis).get("status")).isEqualTo("COMPLETED");
            byte[] analysisSummary=analyses.artifact(analysis,"summary.json").content();
            assertThat(json.readTree(analysisSummary).path("studyCount").asInt()).isOne();
            assertThat(analyses.artifact(analysis,"bundle.zip").content()).isNotEmpty();
            assertThat(jdbc.queryForObject("select count(*) from extracted_field",Integer.class)).isEqualTo(2);
            assertThat(jdbc.queryForObject("select count(*) from analysis_artifact where name like 'figures/%'",Integer.class)).isGreaterThan(0);
            // Reentrega do evento analitico tambem nao duplica artefatos.
            UUID analysisEvent=jdbc.queryForObject("select source_event_id from analysis_run where id=?",UUID.class,analysis);
            int artifactCount=jdbc.queryForObject("select count(*) from analysis_artifact",Integer.class);
            runPython(rabbit,minio,"-c","""
                    import json
                    from denguepharma_workers.runtime import Settings, Worker, QUEUE
                    w=Worker(Settings.from_env()); w.connect()
                    w.channel.basic_publish('',QUEUE,json.dumps({'eventId':'%s','schemaVersion':1}).encode(),mandatory=True)
                    w.consume_one(); w.close()
                    """.formatted(analysisEvent));
            assertThat(jdbc.queryForObject("select count(*) from analysis_artifact",Integer.class)).isEqualTo(artifactCount);
            // Corpus v3 usa o mesmo broker, armazenamento e rotina numerica do comando.
            UUID protocol=jdbc.queryForObject("""
                    insert into protocol(code,version,title,question,sources,strategy,eligibility,cutoff_date,status)
                    values('E2E-CORPUS',1,'Corpus','Q','["PUBMED"]','{"maxRecords":25}','{}','2026-10-27','REGISTERED') returning id
                    """,UUID.class);
            UUID search=jdbc.queryForObject("insert into search_run(protocol_id,source,query,connector_version,status) values(?,'PUBMED','dengue','fixture','COMPLETED') returning id",UUID.class,protocol);
            jdbc.update("insert into search_run_document(search_run_id,document_version_id) values(?,?)",search,version);
            UUID corpusRun=(UUID)corpus.create(new org.denguepharma.analysis.CorpusService.Request(protocol,null),null).get("id");
            runPython(rabbit,minio,"-m","denguepharma_workers.runtime","--once");
            assertThat(analyses.get(corpusRun).get("status")).isEqualTo("COMPLETED");
            var corpusSummary=json.readTree(analyses.artifact(corpusRun,"summary.json").content());
            assertThat(corpusSummary.path("documentCount").asInt()).isOne();
            assertThat(corpusSummary.path("studyCount").asInt()).isOne();
            assertThat(analyses.artifact(corpusRun,"records.json").content()).isNotEmpty();
            // Leitura real verifica arquivo documental e os tres artefatos pelo hash no nome.
            runPython(rabbit, minio, "-c", """
                    import hashlib
                    from denguepharma_workers.runtime import Settings, ObjectStore, BUCKET
                    store=ObjectStore(Settings.from_env())
                    count=0
                    for obj in store.client.list_objects(BUCKET, recursive=True):
                        data=store.read(obj.object_name)
                        expected=obj.object_name.split('/')[2] if obj.object_name.startswith('analyses/') else obj.object_name.rsplit('/',1)[1].split('.')[0]
                        assert hashlib.sha256(data).hexdigest() == expected
                        count+=1
                    assert count > 10, count
                    """);
        }
    }

    private void runPython(GenericContainer<?> rabbit, GenericContainer<?> minio, String... arguments) throws Exception {
        String python = System.getenv("PIPELINE_PYTHON");
        if (python == null || python.isBlank()) throw new IllegalStateException("Defina PIPELINE_PYTHON para o Python com workers instalados");
        var command = new java.util.ArrayList<String>(); command.add(python); command.addAll(List.of(arguments));
        Path log = Path.of("target", "pipeline-e2e-python.log").toAbsolutePath();
        var builder = new ProcessBuilder(command).redirectErrorStream(true).redirectOutput(log.toFile());
        builder.environment().putAll(Map.of(
                "BACKEND_URL", "http://localhost:" + port, "PIPELINE_TOKEN", "pipeline-e2e-token-at-least-32-characters",
                "RABBITMQ_HOST", rabbit.getHost(), "RABBITMQ_PORT", rabbit.getMappedPort(5672).toString(),
                "RABBITMQ_USER", "pipeline", "RABBITMQ_PASSWORD", "pipeline-test-password",
                "MINIO_ENDPOINT", minio.getHost() + ":" + minio.getMappedPort(9000),
                "MINIO_USER", "pipeline", "MINIO_PASSWORD", "pipeline-test-password"));
        builder.environment().put("MINIO_SECURE", "false");
        var process = builder.start();
        if (!process.waitFor(90, TimeUnit.SECONDS)) {
            process.destroyForcibly();
            throw new AssertionError("Worker excedeu o timeout; ver target/pipeline-e2e-python.log");
        }
        assertThat(process.exitValue()).withFailMessage("Worker falhou: %s", Files.readString(log)).isZero();
    }
}
