package org.denguepharma;

import static org.assertj.core.api.Assertions.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.denguepharma.extraction.ExtractionService.ProposedField;
import org.denguepharma.extraction.ExtractionService.RunInput;
import org.denguepharma.pipeline.PipelineService;
import org.denguepharma.user.Role;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.context.TestPropertySource;
import org.springframework.web.server.ResponseStatusException;

@TestPropertySource(properties = "denguepharma.pipeline.token=pipeline-test-token-at-least-32-characters")
class PipelineIntegrationTest extends AbstractIntegrationTest {
    static final String TOKEN = "pipeline-test-token-at-least-32-characters";
    @Autowired PipelineService pipeline;

    @Test
    void credencialDeServicoNaoConfereAcessoAdministrativoEUsuariosNaoAcessamPipeline() throws Exception {
        mvc.perform(post("/api/internal/pipeline/outbox/claim")).andExpect(status().isUnauthorized());
        mvc.perform(post("/api/internal/pipeline/outbox/claim").header("Authorization", tokenFor(Role.ADMINISTRADOR)))
                .andExpect(status().isForbidden());
        mvc.perform(post("/api/internal/pipeline/outbox/claim").header("X-Pipeline-Token", "incorreto"))
                .andExpect(status().isUnauthorized());
        mvc.perform(post("/api/internal/pipeline/outbox/claim").header("X-Pipeline-Token", TOKEN))
                .andExpect(status().isOk()).andExpect(jsonPath("$.length()").value(0));
        mvc.perform(get("/api/admin/users").header("X-Pipeline-Token", TOKEN)).andExpect(status().isUnauthorized());
    }

    @Test
    void publicacaoExigeConfirmacaoETokenReservadoSemExporTexto() throws Exception {
        var seed = seedDocument();
        var claimed = pipeline.claimOutbox(1).get(0);
        assertThat(claimed).doesNotContainKeys("payload", "content", "metadata");
        assertThat(pipeline.claimOutbox(1)).isEmpty();
        assertThatThrownBy(() -> pipeline.confirmOutbox(seed.event, UUID.randomUUID())).isInstanceOf(ResponseStatusException.class);
        assertThat(jdbc.queryForObject("select published_at is null from outbox where event_id = ?", Boolean.class, seed.event)).isTrue();
        pipeline.confirmOutbox(seed.event, (UUID) claimed.get("relay_token"));
        assertThat(jdbc.queryForObject("select published_at is not null from outbox where event_id = ?", Boolean.class, seed.event)).isTrue();
    }

    @Test
    void commitConcluiJobInboxEExtracaoAtomicamenteEReentregaNaoDuplica() throws Exception {
        var seed = seedDocument();
        var claim = pipeline.claimDelivery(seed.event);
        UUID job = (UUID) claim.get("jobId"), lease = (UUID) claim.get("leaseToken");
        assertThat(pipeline.claimDelivery(seed.event).get("state")).isEqualTo("BUSY");
        var input = pipeline.input(job, lease);
        assertThat(input.get("content")).isEqualTo(seed.content);
        assertThatThrownBy(() -> pipeline.completeExtraction(job, lease, extraction(seed.document))).isInstanceOf(ResponseStatusException.class);
        assertThat(jdbc.queryForObject("select count(*) from extraction_run", Integer.class)).isZero();
        pipeline.archive(job, lease, seed.hash, seed.content.getBytes(StandardCharsets.UTF_8).length);
        pipeline.completeExtraction(job, lease, extraction(seed.document));
        assertThat(pipeline.claimDelivery(seed.event).get("state")).isEqualTo("COMPLETED");
        assertThat(jdbc.queryForObject("select count(*) from extracted_field where published", Integer.class)).isZero();
        assertThat(jdbc.queryForObject("select count(*) from extraction_run", Integer.class)).isOne();
        assertThat(jdbc.queryForObject("select processed_at is not null from inbox where event_id = ? and consumer = ?", Boolean.class, seed.event, PipelineService.CONSUMER)).isTrue();
    }

    @Test
    void executorAtrasadoNaoGravaNemInvalidaLeaseMaisNovo() throws Exception {
        var seed = seedDocument();
        var first = pipeline.claimDelivery(seed.event);
        UUID job = (UUID) first.get("jobId"), old = (UUID) first.get("leaseToken");
        pipeline.archive(job, old, seed.hash, seed.content.length());
        jdbc.update("update job set lease_until = clock_timestamp() - interval '1 second' where id = ?", job);
        var next = pipeline.claimDelivery(seed.event);
        UUID fresh = (UUID) next.get("leaseToken");
        assertThat(fresh).isNotEqualTo(old);
        assertThatThrownBy(() -> pipeline.completeExtraction(job, old, extraction(seed.document))).isInstanceOf(ResponseStatusException.class);
        assertThatThrownBy(() -> pipeline.fail(job, old, "OLD_WORKER")).isInstanceOf(ResponseStatusException.class);
        assertThat(jdbc.queryForObject("select count(*) from extraction_run", Integer.class)).isZero();
        assertThat(jdbc.queryForObject("select lease_token from job where id = ?", UUID.class, job)).isEqualTo(fresh);
        pipeline.completeExtraction(job, fresh, extraction(seed.document));
    }

    @Test
    void falhasTemBackoffQuarentenaERetomadaAuditada() throws Exception {
        var seed = seedDocument();
        var claim = pipeline.claimDelivery(seed.event);
        UUID job = (UUID) claim.get("jobId");
        jdbc.update("update job set max_attempts = 2 where id = ?", job);
        assertThat(pipeline.fail(job, (UUID) claim.get("leaseToken"), "STORAGE_UNAVAILABLE").get("status")).isEqualTo("PENDING");
        assertThat(pipeline.claimDelivery(seed.event).get("state")).isEqualTo("BUSY");
        jdbc.update("update job set next_attempt_at = now() - interval '1 second' where id = ?", job);
        claim = pipeline.claimDelivery(seed.event);
        assertThat(pipeline.fail(job, (UUID) claim.get("leaseToken"), "STORAGE_UNAVAILABLE").get("status")).isEqualTo("QUARANTINED");
        assertThat(pipeline.claimDelivery(seed.event).get("state")).isEqualTo("QUARANTINED");
        mvc.perform(post("/api/ops/jobs/" + job + "/retry").header("Authorization", tokenFor(Role.ADMINISTRADOR))
                        .contentType("application/json").content("{\"reason\":\"Armazenamento recuperado\"}"))
                .andExpect(status().isOk());
        assertThat(pipeline.claimDelivery(seed.event).get("state")).isEqualTo("LEASED");
        assertThat(jdbc.queryForObject("select count(*) from audit_log where action = 'JOB_RETRY_AUTHORIZED'", Integer.class)).isOne();
    }

    @Test
    void publicadorRecuperaMensagemPerdidaELeaseExpirado() throws Exception {
        var seed = seedDocument();
        var pub = pipeline.claimOutbox(1).get(0);
        pipeline.confirmOutbox(seed.event, (UUID) pub.get("relay_token"));
        jdbc.update("update outbox set published_at = clock_timestamp() - interval '61 seconds' where event_id = ?", seed.event);
        assertThat(pipeline.claimOutbox(1)).hasSize(1);
        var claim = pipeline.claimDelivery(seed.event);
        jdbc.update("update job set lease_until = clock_timestamp() - interval '1 second' where id = ?", claim.get("jobId"));
        jdbc.update("update outbox set relay_until = clock_timestamp() - interval '1 second', published_at = now() where event_id = ?", seed.event);
        assertThat(pipeline.claimOutbox(1)).hasSize(1);
    }

    private RunInput extraction(UUID document) {
        return new RunInput(document, "rules-2", "DETERMINISTIC_RULES", "rules-2", "rules-hash", "rules", "1",
                List.of(new ProposedField("sample_size", "50", "50", "PRESENTE", "Abstract", null,
                        "char:3-25", "We randomized 50 adult patients", 50)));
    }
    private record Seed(UUID event, UUID document, String content, String hash) {}
    private Seed seedDocument() throws Exception {
        String content = "{\"abstract\":\"We randomized 50 adult patients with DENV-2.\"}";
        String hash = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(content.getBytes(StandardCharsets.UTF_8)));
        UUID study = jdbc.queryForObject("insert into study(title) values('Pipeline test') returning id", UUID.class);
        UUID doc = jdbc.queryForObject("insert into document(doc_type,title) values('PUBLICACAO','Pipeline test') returning id", UUID.class);
        UUID version = jdbc.queryForObject("""
                insert into document_version(document_id, version_no, content_hash, origin, storage_uri, access_status, retrieved_at, metadata, canonical_content)
                values (?,1,?,'PUBMED',?,'SOMENTE_RESUMO',now(),?::jsonb,?) returning id
                """, UUID.class, doc, hash, "s3://denguepharma-corpus/pubmed/" + hash + ".json", content, content);
        jdbc.update("insert into study_document(study_id,document_id,report_role,link_certainty) values(?,?,'PUBLICACAO_PRINCIPAL','CONFIRMADO')", study, doc);
        UUID event = UUID.randomUUID();
        jdbc.update("insert into outbox(event_id,aggregate_type,aggregate_id,event_type,payload) values(?,'document_version',?,'DocumentoImportado','{}')", event, version.toString());
        return new Seed(event, version, content, hash);
    }
}
