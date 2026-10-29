package org.denguepharma.pipeline;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.denguepharma.extraction.ExtractionService;
import org.denguepharma.extraction.ExtractionService.RunInput;
import org.denguepharma.ingest.ImportService;
import org.denguepharma.ops.ReportAndOpsService;
import org.denguepharma.analysis.AnalysisService;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class PipelineService {
    public static final String CONSUMER = "pipeline-v1";
    private final JdbcTemplate jdbc;
    private final ObjectMapper json;
    private final ExtractionService extractions;
    private final ReportAndOpsService reports;
    private final AnalysisService analyses;

    public PipelineService(JdbcTemplate jdbc, ObjectMapper json, ExtractionService extractions, ReportAndOpsService reports, AnalysisService analyses) {
        this.jdbc = jdbc; this.json = json; this.extractions = extractions; this.reports = reports; this.analyses = analyses;
    }

    /** Reserva curta. Chamadas a broker/storage acontecem depois desta transacao. */
    @Transactional
    public List<Map<String, Object>> claimOutbox(int limit) {
        jdbc.update("update outbox set last_error = 'UNSUPPORTED_SCHEMA' where published_at is null and schema_version <> 1 and last_error is distinct from 'UNSUPPORTED_SCHEMA'");
        jdbc.update("""
                update job set status = 'QUARANTINED', lease_token = null, lease_until = null,
                    last_error = 'lease expirado no limite de tentativas', updated_at = now()
                where source_event_id is not null and status = 'LEASED' and lease_until < clock_timestamp()
                  and attempts >= max_attempts
                """);
        // Reconstroi a entrega perdida entre confirmacao do broker e inicio do consumidor.
        jdbc.update("""
                update outbox o set published_at = null
                where o.published_at is not null
                  and o.event_type in ('DocumentoImportado','FonteAlterada','RelatorioSolicitado','AnaliseSolicitada')
                  and ((o.published_at < clock_timestamp() - interval '60 seconds'
                        and not exists (select 1 from job j where j.source_event_id = o.event_id))
                    or exists (select 1 from job j where j.source_event_id = o.event_id
                        and ((j.status = 'PENDING' and j.next_attempt_at <= clock_timestamp())
                          or (j.status = 'LEASED' and j.lease_until < clock_timestamp() and j.attempts < j.max_attempts))))
                """);
        return jdbc.queryForList("""
                with ready as (
                    select o.id from outbox o where o.published_at is null
                      and o.schema_version = 1
                      and o.event_type in ('DocumentoImportado','FonteAlterada','RelatorioSolicitado','AnaliseSolicitada')
                      and o.next_attempt_at <= clock_timestamp()
                      and (o.relay_until is null or o.relay_until < clock_timestamp())
                      and not exists (select 1 from job j where j.source_event_id = o.event_id
                                      and j.status in ('COMPLETED','QUARANTINED'))
                    order by o.priority desc, o.created_at asc limit ? for update skip locked
                )
                update outbox o set relay_token = gen_random_uuid(), relay_until = clock_timestamp() + interval '60 seconds',
                    attempts = o.attempts + 1
                from ready where o.id = ready.id
                returning o.event_id, o.event_type, o.schema_version, o.relay_token, o.priority
                """, Math.max(1, Math.min(limit, 50)));
    }

    @Transactional
    public void confirmOutbox(UUID event, UUID token) {
        int count = jdbc.update("""
                update outbox set published_at = clock_timestamp(), relay_token = null, relay_until = null, last_error = null
                where event_id = ? and relay_token = ? and relay_until >= clock_timestamp()
                """, event, token);
        require(count == 1, "reserva de publicacao expirada");
    }

    @Transactional
    public void failOutbox(UUID event, UUID token) {
        jdbc.update("""
                update outbox set relay_token = null, relay_until = null, last_error = 'falha na confirmacao do broker',
                    next_attempt_at = clock_timestamp() + (least(300, power(2, least(attempts, 8))) + random() * 3) * interval '1 second'
                where event_id = ? and relay_token = ? and relay_until >= clock_timestamp()
                """, event, token);
    }

    @Transactional
    public Map<String, Object> claimDelivery(UUID event) {
        List<Map<String, Object>> rows = jdbc.queryForList("select event_type, aggregate_id, schema_version from outbox where event_id = ?", event);
        if (rows.isEmpty()) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "evento desconhecido");
        var source = rows.get(0);
        require(((Number) source.get("schema_version")).intValue() == 1, "schema de evento nao suportado");
        String jobType = switch ((String) source.get("event_type")) {
            case "DocumentoImportado", "FonteAlterada" -> "EXTRACT_DOCUMENT";
            case "RelatorioSolicitado" -> "GENERATE_REPORT";
            case "AnaliseSolicitada" -> "ANALYZE_EVIDENCE";
            default -> throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, "evento sem consumidor nesta versao");
        };
        jdbc.update("""
                insert into job (job_type, ref_id, source_event_id) values (?, ?, ?) on conflict (source_event_id) do nothing
                """, jobType, source.get("aggregate_id"), event);
        var job = jdbc.queryForMap("select * from job where source_event_id = ? for update", event);
        String status = (String) job.get("status");
        if (Set.of("COMPLETED", "QUARANTINED").contains(status)) return Map.of("state", status, "jobId", job.get("id"));
        UUID token = UUID.randomUUID();
        int count = jdbc.update("""
                update job set status = 'LEASED', lease_token = ?, lease_until = clock_timestamp() + interval '120 seconds',
                    attempts = attempts + 1, updated_at = now()
                where id = ? and attempts < max_attempts and next_attempt_at <= clock_timestamp()
                  and (status = 'PENDING' or (status = 'LEASED' and lease_until < clock_timestamp()))
                """, token, job.get("id"));
        if (count == 0) return Map.of("state", "BUSY", "jobId", job.get("id"));
        jdbc.update("insert into inbox (event_id, consumer) values (?, ?) on conflict do nothing", event, CONSUMER);
        return Map.of("state", "LEASED", "jobId", job.get("id"), "leaseToken", token,
                "jobType", jobType, "refId", job.get("ref_id"));
    }

    @Transactional
    public void renew(UUID job, UUID token) {
        require(jdbc.update("""
                update job set lease_until = clock_timestamp() + interval '120 seconds', updated_at = now()
                where id = ? and lease_token = ? and status = 'LEASED' and lease_until >= clock_timestamp()
                """, job, token) == 1, "lease expirado");
    }

    @Transactional(readOnly = true)
    public Map<String, Object> input(UUID id, UUID token) {
        var job = leasedJob(id, token, false);
        UUID ref = UUID.fromString((String) job.get("ref_id"));
        if ("ANALYZE_EVIDENCE".equals(job.get("job_type"))) return analyses.input(ref);
        if ("GENERATE_REPORT".equals(job.get("job_type"))) return Map.of("snapshot", reports.getSnapshot(ref));
        var doc = jdbc.queryForMap("select id, content_hash, origin, storage_uri, metadata::text as metadata, canonical_content from document_version where id = ?", ref);
        String canonical = (String) doc.remove("canonical_content");
        String metadata = (String) doc.remove("metadata");
        String content = canonical == null ? write(ImportService.canonical(read(metadata))) : canonical;
        require(sha256(content.getBytes(StandardCharsets.UTF_8)).equals(doc.get("content_hash")), "hash documental divergente");
        doc.put("content", content);
        return doc;
    }

    @Transactional
    public void archive(UUID id, UUID token, String hash, long size) {
        var job = leasedJob(id, token, true);
        require("EXTRACT_DOCUMENT".equals(job.get("job_type")), "tipo de job invalido");
        UUID ref = UUID.fromString((String) job.get("ref_id"));
        var doc = jdbc.queryForMap("select storage_uri, content_hash from document_version where id = ?", ref);
        require(hash.equals(doc.get("content_hash")) && size > 0, "arquivo divergente da versao documental");
        String content = (String) input(id, token).get("content");
        require(size == content.getBytes(StandardCharsets.UTF_8).length, "tamanho documental divergente");
        jdbc.update("""
                insert into document_archive (document_version_id, storage_uri, content_hash, size_bytes)
                values (?, ?, ?, ?) on conflict (document_version_id) do nothing
                """, ref, doc.get("storage_uri"), hash, size);
    }

    /** Resultado, Inbox e conclusao do job sao um unico commit protegido pelo token vigente. */
    @Transactional
    public Map<String, Object> completeExtraction(UUID id, UUID token, RunInput input) {
        var job = leasedJob(id, token, true);
        require("EXTRACT_DOCUMENT".equals(job.get("job_type")) && input.documentVersionId().toString().equals(job.get("ref_id")), "documento nao pertence ao job");
        require(Boolean.TRUE.equals(jdbc.queryForObject("select exists (select 1 from document_archive where document_version_id = ?)", Boolean.class, input.documentVersionId())), "documento ainda nao arquivado");
        var result = extractions.submitExtraction(input, null);
        complete(job, token, (UUID) result.get("extractionRunId"));
        return result;
    }

    @Transactional
    public Map<String, Object> fail(UUID id, UUID token, String errorCode) {
        var job = leasedJob(id, token, true);
        String status = ((Number) job.get("attempts")).intValue() >= ((Number) job.get("max_attempts")).intValue() ? "QUARANTINED" : "PENDING";
        // Somente codigo curto; nunca persistir resposta externa que possa conter chaves/texto restrito.
        String code = errorCode != null && errorCode.matches("[A-Z_]{1,64}") ? errorCode : "PROCESSING_FAILED";
        jdbc.update("""
                update job set status = ?, lease_token = null, lease_until = null, last_error = ?,
                    next_attempt_at = clock_timestamp() + (least(300, power(2, least(attempts, 8))) + random()*3) * interval '1 second',
                    updated_at = now() where id = ?
                """, status, code, id);
        jdbc.update("""
                update outbox set published_at = null, next_attempt_at = (select next_attempt_at from job where id = ?)
                where event_id = ?
                """, id, job.get("source_event_id"));
        return Map.of("status", status);
    }

    @Transactional(readOnly = true)
    public byte[] reportFile(UUID id, UUID token, String format) {
        var job = leasedJob(id, token, false);
        require("GENERATE_REPORT".equals(job.get("job_type")), "tipo de job invalido");
        UUID ref = UUID.fromString((String) job.get("ref_id"));
        return switch (format) {
            case "pdf" -> reports.exportPdf(ref);
            case "csv" -> reports.exportCsv(ref);
            case "json" -> write(reports.getSnapshot(ref)).getBytes(StandardCharsets.UTF_8);
            default -> throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, "formato invalido");
        };
    }

    public record Artifact(String format, String contentHash, long sizeBytes) {}
    @Transactional
    public void completeAnalysis(UUID id, UUID token, byte[] bundle) {
        var job = leasedJob(id, token, true);
        require("ANALYZE_EVIDENCE".equals(job.get("job_type")), "tipo de job invalido");
        analyses.persist(UUID.fromString((String) job.get("ref_id")), bundle);
        complete(job, token, null);
    }
    @Transactional
    public void completeReport(UUID id, UUID token, List<Artifact> artifacts) {
        var job = leasedJob(id, token, true);
        require("GENERATE_REPORT".equals(job.get("job_type")), "tipo de job invalido");
        require(artifacts != null && artifacts.size() == 3
                && artifacts.stream().map(Artifact::format).collect(java.util.stream.Collectors.toSet()).equals(Set.of("pdf", "csv", "json")), "manifesto incompleto");
        UUID ref = UUID.fromString((String) job.get("ref_id"));
        for (var artifact : artifacts) {
            require(artifact.sizeBytes() > 0 && artifact.contentHash() != null && artifact.contentHash().matches("[a-f0-9]{64}"), "artefato invalido");
            byte[] expected = reportFile(id, token, artifact.format());
            require(expected.length == artifact.sizeBytes() && sha256(expected).equals(artifact.contentHash()), "artefato nao corresponde ao snapshot");
            jdbc.update("""
                    insert into report_artifact (report_snapshot_id, format, content_hash, size_bytes, storage_uri)
                    values (?, ?, ?, ?, ?) on conflict do nothing
                    """, ref, artifact.format(), artifact.contentHash(), artifact.sizeBytes(),
                    "s3://denguepharma-corpus/reports/" + ref + "/" + artifact.contentHash() + "." + artifact.format());
        }
        complete(job, token, null);
    }

    private Map<String, Object> leasedJob(UUID id, UUID token, boolean lock) {
        var rows = jdbc.queryForList("select * from job where id = ? and source_event_id is not null and status = 'LEASED' and lease_token = ? and lease_until >= clock_timestamp()" + (lock ? " for update" : ""), id, token);
        require(!rows.isEmpty(), "lease expirado ou token invalido");
        return rows.get(0);
    }
    private void complete(Map<String, Object> job, UUID token, UUID run) {
        require(jdbc.update("""
                update job set status = 'COMPLETED', extraction_run_id = ?, lease_token = null, lease_until = null, last_error = null, updated_at = now()
                where id = ? and lease_token = ? and lease_until >= clock_timestamp()
                """, run, job.get("id"), token) == 1, "lease expirou antes do commit");
        jdbc.update("update inbox set processed_at = now() where event_id = ? and consumer = ?", job.get("source_event_id"), CONSUMER);
    }
    private void require(boolean condition, String reason) {
        if (!condition) throw new ResponseStatusException(HttpStatus.CONFLICT, reason);
    }
    private JsonNode read(String text) {
        try { return json.readTree(text); } catch (JsonProcessingException e) { throw new IllegalStateException(e); }
    }
    private String write(Object value) {
        try { return json.writeValueAsString(value); } catch (JsonProcessingException e) { throw new IllegalStateException(e); }
    }
    private String sha256(byte[] data) {
        try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(data)); }
        catch (java.security.NoSuchAlgorithmException e) { throw new IllegalStateException(e); }
    }
}
