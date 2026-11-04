package org.denguepharma.pipeline;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.denguepharma.analysis.AnalysisService;
import org.denguepharma.extraction.ExtractionService;
import org.denguepharma.ops.ReportAndOpsService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Testes unitários para resiliência transacional e idempotência:
 * - REQ-OPS-001 (ACC-OPS-001 / P10): Estabilidade do event_id no Outbox e controle de publicação.
 * - REQ-OPS-002 (ACC-OPS-002 / T7 / P10): Idempotência estrita no Inbox protegendo contra reexecução.
 */
class TransactionalOutboxInboxUnitTest {

    private JdbcTemplate jdbc;
    private ObjectMapper json;
    private ExtractionService extractions;
    private ReportAndOpsService reports;
    private AnalysisService analyses;
    private PipelineService pipelineService;

    @BeforeEach
    void setUp() {
        jdbc = mock(JdbcTemplate.class);
        json = new ObjectMapper();
        extractions = mock(ExtractionService.class);
        reports = mock(ReportAndOpsService.class);
        analyses = mock(AnalysisService.class);
        pipelineService = new PipelineService(jdbc, json, extractions, reports, analyses);
    }

    @Test
    void confirmOutboxSucceedsWhenLeaseValidAndThrowsWhenExpired() {
        UUID eventId = UUID.randomUUID();
        UUID token = UUID.randomUUID();

        // 1. Simula confirmação bem-sucedida (1 linha afetada com o mesmo event_id)
        when(jdbc.update(anyString(), eq(eventId), eq(token))).thenReturn(1);
        pipelineService.confirmOutbox(eventId, token);
        verify(jdbc).update(anyString(), eq(eventId), eq(token));

        // 2. Simula lease expirado (0 linhas afetadas) -> deve lançar ResponseStatusException (400)
        when(jdbc.update(anyString(), eq(eventId), eq(token))).thenReturn(0);
        assertThatThrownBy(() -> pipelineService.confirmOutbox(eventId, token))
                .isInstanceOf(ResponseStatusException.class)
                .hasMessageContaining("reserva de publicacao expirada");
    }

    @Test
    void failOutboxResetsLeasePreservingStableEventId() {
        UUID eventId = UUID.randomUUID();
        UUID token = UUID.randomUUID();

        // REQ-OPS-001: Ao registrar falha de confirmação no broker, o event_id estável permanece
        // inalterado para nova tentativa
        pipelineService.failOutbox(eventId, token);
        verify(jdbc).update(anyString(), eq(eventId), eq(token));
    }

    @Test
    void claimDeliveryOnCompletedEventReturnsCompletedWithoutNewLease() {
        UUID eventId = UUID.randomUUID();
        UUID jobId = UUID.randomUUID();

        // Simula evento existente no Outbox
        when(jdbc.queryForList(eq("select event_type, aggregate_id, schema_version from outbox where event_id = ?"), eq(eventId)))
                .thenReturn(List.of(Map.of(
                        "event_type", "DocumentoImportado",
                        "aggregate_id", UUID.randomUUID(),
                        "schema_version", 1
                )));

        // Simula job já COMPLETED (REQ-OPS-002 / T7: Entrega duplicada não repete o efeito)
        when(jdbc.queryForMap(eq("select * from job where source_event_id = ? for update"), eq(eventId)))
                .thenReturn(Map.of(
                        "id", jobId,
                        "status", "COMPLETED"
                ));

        Map<String, Object> result = pipelineService.claimDelivery(eventId);

        assertThat(result.get("state")).isEqualTo("COMPLETED");
        assertThat(result.get("jobId")).isEqualTo(jobId);
        // Não aloca novo lease nem leaseToken
        assertThat(result.containsKey("leaseToken")).isFalse();
    }

    @Test
    void claimDeliveryOnQuarantinedEventReturnsQuarantinedWithoutNewLease() {
        UUID eventId = UUID.randomUUID();
        UUID jobId = UUID.randomUUID();

        when(jdbc.queryForList(eq("select event_type, aggregate_id, schema_version from outbox where event_id = ?"), eq(eventId)))
                .thenReturn(List.of(Map.of(
                        "event_type", "DocumentoImportado",
                        "aggregate_id", UUID.randomUUID(),
                        "schema_version", 1
                )));

        // Job em quarentena não pode ser executado novamente
        when(jdbc.queryForMap(eq("select * from job where source_event_id = ? for update"), eq(eventId)))
                .thenReturn(Map.of(
                        "id", jobId,
                        "status", "QUARANTINED"
                ));

        Map<String, Object> result = pipelineService.claimDelivery(eventId);

        assertThat(result.get("state")).isEqualTo("QUARANTINED");
        assertThat(result.get("jobId")).isEqualTo(jobId);
        assertThat(result.containsKey("leaseToken")).isFalse();
    }

    @Test
    void claimDeliveryRegistersInInboxOnNewDelivery() {
        UUID eventId = UUID.randomUUID();
        UUID jobId = UUID.randomUUID();

        when(jdbc.queryForList(eq("select event_type, aggregate_id, schema_version from outbox where event_id = ?"), eq(eventId)))
                .thenReturn(List.of(Map.of(
                        "event_type", "DocumentoImportado",
                        "aggregate_id", UUID.randomUUID(),
                        "schema_version", 1
                )));

        // Job em estado PENDING
        when(jdbc.queryForMap(eq("select * from job where source_event_id = ? for update"), eq(eventId)))
                .thenReturn(Map.of(
                        "id", jobId,
                        "status", "PENDING",
                        "ref_id", UUID.randomUUID()
                ));

        // Update de lease no job afeta 1 linha
        when(jdbc.update(anyString(), any(UUID.class), eq(jobId))).thenReturn(1);

        Map<String, Object> result = pipelineService.claimDelivery(eventId);

        assertThat(result.get("state")).isEqualTo("LEASED");
        assertThat(result.get("jobId")).isEqualTo(jobId);
        assertThat(result.containsKey("leaseToken")).isTrue();

        // REQ-OPS-002: Verifica que houve o registro formal na tabela inbox com "on conflict do nothing"
        verify(jdbc).update(
                eq("insert into inbox (event_id, consumer) values (?, ?) on conflict do nothing"),
                eq(eventId),
                eq(PipelineService.CONSUMER)
        );
    }
}

