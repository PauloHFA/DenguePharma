package org.denguepharma.ops;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.denguepharma.audit.AuditService;
import org.denguepharma.catalog.CatalogService;
import org.denguepharma.catalog.CatalogService.CatalogFilter;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

/**
 * RF-09, RF-10, RF-11, RF-12, RNF-03, RNF-04 e Cenários T7, T8, T9:
 * Geração de relatórios reproduzíveis (PDF/CSV/JSON), fila de reavaliação de mudanças de fonte,
 * processamento confiável Outbox/Inbox/Job com lease e quarentena, e pacote de reprodução respeitando licenças.
 */
@Service
public class ReportAndOpsService {

    /** Licenças abertas que autorizam redistribuição de texto integral (RNF-03, T9). */
    public static final Set<String> REDISTRIBUTABLE_LICENSES = Set.of(
            "CC-BY", "CC-BY-4.0", "CC0", "PUBLIC_DOMAIN");

    private final JdbcTemplate jdbc;
    private final ObjectMapper om;
    private final CatalogService catalog;
    private final AuditService audit;

    public ReportAndOpsService(JdbcTemplate jdbc, ObjectMapper om, CatalogService catalog, AuditService audit) {
        this.jdbc = jdbc;
        this.om = om;
        this.catalog = catalog;
        this.audit = audit;
    }

    // ==================== RF-09 & T8: Relatórios reproduzíveis ====================

    @Transactional
    public Map<String, Object> createSnapshot(CatalogFilter filter, UUID actor) {
        List<Map<String, Object>> studies = catalog.search(filter);
        Instant generatedAt = Instant.now();

        ArrayNode refs = om.createArrayNode();
        for (Map<String, Object> st : studies) {
            UUID studyId = (UUID) st.get("id");
            List<Map<String, Object>> docs = jdbc.queryForList("""
                    select dv.id as document_version_id, dv.origin as source, dv.version_no,
                           dv.content_hash, dv.license, dv.access_status, dv.retrieved_at
                    from document_version dv
                    join study_document sd on sd.document_id = dv.document_id
                    where sd.study_id = ?
                    order by dv.version_no desc
                    """, studyId);
            for (Map<String, Object> d : docs) {
                ObjectNode ref = om.createObjectNode();
                ref.put("study_id", studyId.toString());
                ref.put("document_version_id", String.valueOf(d.get("document_version_id")));
                ref.put("source", (String) d.get("source"));
                ref.put("version_no", ((Number) d.get("version_no")).intValue());
                ref.put("content_hash", (String) d.get("content_hash"));
                String lic = (String) d.get("license");
                ref.put("license", lic == null ? "RESTRITA_NAO_REDISTRIBUIVEL" : lic);
                ref.put("full_text_redistributable", isRedistributable(lic));
                ref.put("retrieved_at", String.valueOf(d.get("retrieved_at")));
                refs.add(ref);
            }
        }

        ObjectNode dataNode = om.createObjectNode();
        dataNode.put("generated_at", generatedAt.toString());
        dataNode.put("disclaimer", "Uso exclusivo para pesquisa e sintese de evidencias. Nao constitui prescricao nem recomendacao de dose.");
        dataNode.set("studies", om.valueToTree(studies));

        UUID snapshotId = UUID.randomUUID();
        jdbc.update("""
                insert into report_snapshot (id, requested_by, filters, data, refs)
                values (?, ?, ?::jsonb, ?::jsonb, ?::jsonb)
                """, snapshotId, actor, write(filter), write(dataNode), write(refs));

        ObjectNode evt = om.createObjectNode();
        evt.put("report_snapshot_id", snapshotId.toString());
        jdbc.update("""
                insert into outbox (event_id, aggregate_type, aggregate_id, event_type, payload)
                values (?, 'report_snapshot', ?, 'RelatorioSolicitado', ?::jsonb)
                """, UUID.randomUUID(), snapshotId.toString(), write(evt));

        audit.record(actor, "REPORT_GENERATED", "report_snapshot", snapshotId.toString(),
                null, "{\"studyCount\":" + studies.size() + "}", null);

        return getSnapshot(snapshotId);
    }

    public List<Map<String, Object>> listSnapshots() {
        return jdbc.queryForList("""
                select id, requested_by, filters::text as filters, created_at,
                       jsonb_array_length(coalesce(data->'studies', '[]'::jsonb)) as study_count
                from report_snapshot
                order by created_at desc
                """);
    }

    public Map<String, Object> getSnapshot(UUID id) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
                select id, requested_by, filters::text as filters, data::text as data, refs::text as refs, created_at
                from report_snapshot where id = ?
                """, id);
        if (rows.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "relatorio nao encontrado");
        }
        Map<String, Object> r = rows.get(0);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("id", r.get("id"));
        Object createdAtObj = r.get("created_at");
        String createdAtStr = createdAtObj instanceof java.sql.Timestamp ts
                ? ts.toInstant().toString()
                : String.valueOf(createdAtObj);
        out.put("createdAt", createdAtStr);
        out.put("filters", read((String) r.get("filters")));
        out.put("data", read((String) r.get("data")));
        out.put("refs", read((String) r.get("refs")));
        return out;
    }

    public byte[] exportCsv(UUID snapshotId) {
        Map<String, Object> snap = getSnapshot(snapshotId);
        JsonNode data = (JsonNode) snap.get("data");
        JsonNode refs = (JsonNode) snap.get("refs");
        String createdAt = (String) snap.get("createdAt");

        StringBuilder sb = new StringBuilder();
        sb.append("report_id,generated_at,study_id,title,substance,context,purpose,design,phase,serotype,outcome,effect,status_evidencia,limitations,sources_and_hashes,filters\n");
        for (JsonNode st : data.path("studies")) {
            String sid = st.path("id").asText("");
            List<String> srcInfo = new ArrayList<>();
            for (JsonNode ref : refs) {
                if (sid.equals(ref.path("study_id").asText())) {
                    srcInfo.add(ref.path("source").asText() + "#v" + ref.path("version_no").asInt()
                            + "(" + ref.path("content_hash").asText("") + ")");
                }
            }
            sb.append(csv(snapshotId.toString())).append(',')
              .append(csv(createdAt)).append(',')
              .append(csv(sid)).append(',')
              .append(csv(st.path("title").asText(""))).append(',')
              .append(csv(st.path("substance_published_name").asText(""))).append(',')
              .append(csv(st.path("context").asText(""))).append(',')
              .append(csv(st.path("purpose").asText(""))).append(',')
              .append(csv(st.path("design").asText(""))).append(',')
              .append(csv(st.path("phase").asText(""))).append(',')
              .append(csv(st.path("serotype").asText(""))).append(',')
              .append(csv(st.path("outcome_summary").asText(""))).append(',')
              .append(csv(st.path("effect_summary").asText(""))).append(',')
              .append(csv("APROVADO_REVISAO_HUMANA")).append(',')
              .append(csv(st.path("limitations").asText(""))).append(',')
              .append(csv(String.join("; ", srcInfo))).append(',')
              .append(csv(String.valueOf(snap.get("filters")))).append('\n');
        }
        return sb.toString().getBytes(StandardCharsets.UTF_8);
    }

    /**
     * Cenário T8: Gera PDF válido (%PDF-1.4) informando explicitamente fonte, data, contexto,
     * filtros, limitações e status da evidência.
     */
    public byte[] exportPdf(UUID snapshotId) {
        Map<String, Object> snap = getSnapshot(snapshotId);
        JsonNode data = (JsonNode) snap.get("data");
        JsonNode refs = (JsonNode) snap.get("refs");
        JsonNode filters = (JsonNode) snap.get("filters");
        String createdAt = (String) snap.get("createdAt");

        List<String> lines = new ArrayList<>();
        lines.add("DENGUEPHARMA - RELATORIO AUDITAVEL DE EVIDENCIAS");
        lines.add("Relatorio ID: " + snapshotId);
        lines.add("Data de geracao (UTC): " + createdAt);
        lines.add("Filtros aplicados: " + filters.toString());
        lines.add("Status da evidencia: REVISADA E APROVADA POR CURADORIA HUMANA");
        lines.add("Aviso: Uso exclusivo para pesquisa. Nao realiza diagnostico nem prescricao.");
        lines.add("----------------------------------------------------------------------");

        for (JsonNode st : data.path("studies")) {
            String sid = st.path("id").asText("");
            lines.add("Estudo: " + st.path("title").asText(sid));
            lines.add("  Contexto experimental (RC-01): " + st.path("context").asText("NAO_CLASSIFICADO")
                    + " | Finalidade: " + st.path("purpose").asText("NAO_INFORMADO"));
            lines.add("  Substancia: " + st.path("substance_published_name").asText("N/A")
                    + " | Desenho: " + st.path("design").asText("N/A")
                    + " | Sorotipo: " + st.path("serotype").asText("N/A"));
            lines.add("  Desfecho: " + st.path("outcome_summary").asText("N/A")
                    + " | Resultado: " + st.path("effect_summary").asText("N/A"));
            lines.add("  Status Regulatorio (RC-02): " + st.path("regulatory_status").asText("CANDIDATO_EM_PESQUISA"));
            lines.add("  Limitacoes: " + st.path("limitations").asText(""));
            for (JsonNode ref : refs) {
                if (sid.equals(ref.path("study_id").asText())) {
                    lines.add("  Fonte documental: " + ref.path("source").asText()
                            + " v" + ref.path("version_no").asInt()
                            + " | Hash: " + ref.path("content_hash").asText()
                            + " | Licenca: " + ref.path("license").asText());
                }
            }
            lines.add("----------------------------------------------------------------------");
        }
        return buildMinimalPdf(lines);
    }

    // ==================== RNF-03, RF-12 & T9: Pacote de reprodução ====================

    /**
     * Exporta pacote de reprodução permitido pelas licenças (RF-12, RNF-03, T9).
     * Textos integrais de documentos sem licença aberta de redistribuição são omitidos,
     * publicando apenas IDs, hashes, schemas, versões e anotações aprovadas.
     */
    public Map<String, Object> exportReproductionPackage() {
        List<Map<String, Object>> protocols = jdbc.queryForList(
                "select id, code, version, title, question, sources::text as sources, strategy::text as strategy, cutoff_date, status from protocol where status <> 'DRAFT'");
        List<Map<String, Object>> documents = jdbc.queryForList("""
                select dv.id as document_version_id, dv.document_id, dv.version_no, dv.content_hash,
                       dv.origin, dv.license, dv.access_status, dv.retrieved_at, dv.metadata::text as metadata
                from document_version dv
                order by dv.created_at asc
                """);

        List<Map<String, Object>> sanitizedDocs = new ArrayList<>();
        for (Map<String, Object> d : documents) {
            String license = (String) d.get("license");
            boolean canRedistribute = isRedistributable(license);
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("documentVersionId", d.get("document_version_id"));
            item.put("documentId", d.get("document_id"));
            item.put("versionNo", d.get("version_no"));
            item.put("contentHash", d.get("content_hash"));
            item.put("origin", d.get("origin"));
            item.put("license", license == null ? "UNSPECIFIED_RESTRICTED" : license);
            item.put("redistributableFullText", canRedistribute);
            if (canRedistribute && d.get("metadata") != null) {
                item.put("content", read((String) d.get("metadata")));
            } else {
                // T9: Não redistribuir texto sem licença adequada; exportar apenas IDs e hash.
                item.put("content", null);
                item.put("redistributionNotice", "T9/RNF-03: Texto omitido por restricao ou ausencia de licenca aberta.");
            }
            sanitizedDocs.add(item);
        }

        List<Map<String, Object>> annotations = jdbc.queryForList("""
                select ef.id, ef.study_id, ef.field_name, ef.normalized_value, ef.absence_status,
                       ef.review_status, ef.published, er.document_version_id, er.model_version, er.prompt_hash, er.schema_version
                from extracted_field ef
                join extraction_run er on er.id = ef.extraction_run_id
                where ef.published = true
                """);

        Map<String, Object> pkg = new LinkedHashMap<>();
        pkg.put("exportedAt", Instant.now().toString());
        pkg.put("protocols", protocols);
        pkg.put("documentManifest", sanitizedDocs);
        pkg.put("approvedAnnotations", annotations);
        return pkg;
    }

    // ==================== RF-10: Fila de reavaliação ====================

    public List<Map<String, Object>> listReassessments() {
        return jdbc.queryForList("""
                select rt.id, rt.study_id, s.title as study_title, rt.document_version_id,
                       rt.trigger_type, rt.status, rt.notes, rt.created_at, rt.resolved_at
                from reassessment_task rt
                join study s on s.id = rt.study_id
                order by rt.created_at desc
                """);
    }

    @Transactional
    public void resolveReassessment(UUID id, String notes, UUID actor) {
        int n = jdbc.update("""
                update reassessment_task set status = 'RESOLVED', notes = coalesce(?, notes),
                       resolved_by = ?, resolved_at = now()
                where id = ? and status = 'PENDING'
                """, notes, actor, id);
        if (n == 0) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "tarefa de reavaliacao nao encontrada ou ja resolvida");
        }
        audit.record(actor, "REASSESSMENT_RESOLVED", "reassessment_task", id.toString(), null, null, notes);
    }

    // ==================== RF-11 & T7: Outbox / Inbox / Jobs com Lease ====================

    /** Registra consumo idempotente na Inbox (T7). Retorna true apenas na primeira entrega para o consumidor. */
    @Transactional
    public boolean registerInboxDelivery(UUID eventId, String consumer) {
        return jdbc.update("insert into inbox (event_id, consumer, processed_at) values (?, ?, now()) on conflict do nothing", eventId, consumer) == 1;
    }

    @Transactional
    public Map<String, Object> enqueueJob(String jobType, String refId, int maxAttempts, UUID actor) {
        UUID id = UUID.randomUUID();
        jdbc.update("""
                insert into job (id, job_type, ref_id, status, max_attempts)
                values (?, ?, ?, 'PENDING', ?)
                """, id, jobType, refId, maxAttempts <= 0 ? 5 : maxAttempts);
        audit.record(actor, "JOB_ENQUEUED", "job", id.toString(), null,
                "{\"jobType\":\"" + jobType + "\",\"refId\":\"" + refId + "\"}", null);
        return Map.of("jobId", id, "status", "PENDING");
    }

    /** Reserva tarefa por lease com token exclusivo (Seção 13). */
    @Transactional
    public Map<String, Object> acquireLease(UUID jobId, int leaseSeconds) {
        UUID token = UUID.randomUUID();
        int n = jdbc.update("""
                update job
                set status = 'LEASED', lease_token = ?, lease_until = now() + (? || ' seconds')::interval,
                    attempts = attempts + 1, updated_at = now()
                where id = ? and source_event_id is null
                  and (status = 'PENDING' or (status = 'LEASED' and lease_until < now()))
                """, token, Math.max(5, leaseSeconds), jobId);
        if (n == 0) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "job indisponivel para lease");
        }
        return Map.of("jobId", jobId, "leaseToken", token);
    }

    /** Conclui tarefa exigindo o lease_token vigente; resultado atrasado com token inválido é bloqueado (Seção 13). */
    @Transactional
    public void completeJobWithLease(UUID jobId, UUID leaseToken) {
        int n = jdbc.update("""
                update job
                set status = 'COMPLETED', lease_token = null, lease_until = null, updated_at = now()
                where id = ? and source_event_id is null and status = 'LEASED' and lease_token = ? and lease_until >= now()
                """, jobId, leaseToken);
        if (n == 0) {
            throw new ResponseStatusException(HttpStatus.CONFLICT,
                    "lease expirado ou token invalido: resultado atrasado descartado para nao sobrescrever estado vigente");
        }
    }

    /** Registra falha de job; ao atingir max_attempts move automaticamente para QUARANTINED (Seção 13). */
    @Transactional
    public Map<String, Object> failJob(UUID jobId, String errorMessage) {
        List<Map<String, Object>> rows = jdbc.queryForList(
                "select attempts, max_attempts from job where id = ? and source_event_id is null", jobId);
        if (rows.isEmpty()) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "job nao encontrado");
        int attempts = ((Number) rows.get(0).get("attempts")).intValue();
        int maxAttempts = ((Number) rows.get(0).get("max_attempts")).intValue();
        String nextStatus = attempts >= maxAttempts ? "QUARANTINED" : "PENDING";

        jdbc.update("""
                update job
                set status = ?, lease_token = null, lease_until = null, last_error = ?, updated_at = now()
                where id = ?
                """, nextStatus, errorMessage, jobId);
        return Map.of("jobId", jobId, "status", nextStatus, "attempts", attempts);
    }

    /** Reprocessamento autorizado e auditado de job falho/ em quarentena (RF-11). */
    @Transactional
    public Map<String, Object> retryJob(UUID jobId, String reason, UUID actor) {
        int n = jdbc.update("""
                update job
                set status = 'PENDING', attempts = 0, lease_token = null, lease_until = null,
                    last_error = null, next_attempt_at = now(), updated_at = now()
                where id = ? and status in ('FAILED','QUARANTINED')
                """, jobId);
        if (n == 0) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "somente jobs FAILED ou QUARANTINED podem ser reprocessados");
        }
        audit.record(actor, "JOB_RETRY_AUTHORIZED", "job", jobId.toString(), null, null, reason);
        return Map.of("jobId", jobId, "status", "PENDING");
    }

    /**
     * Antecipar o envio nao equivale a publica-lo. O worker marca published_at somente apos confirmacao do broker.
     */
    @Transactional
    public Map<String, Object> relayOutboxBatch(int limit) {
        int scheduled = jdbc.update("""
                update outbox set next_attempt_at = now() where id in (
                  select id from outbox where published_at is null
                    and event_type in ('DocumentoImportado','FonteAlterada','RelatorioSolicitado','AnaliseSolicitada')
                    and (relay_until is null or relay_until < now()) order by priority desc, created_at limit ?)
                """, Math.max(1, Math.min(limit, 100)));
        return Map.of("scheduledEvents", scheduled, "publishedEvents", 0,
                "notice", "O worker publicara os eventos com confirmacao do RabbitMQ.");
    }

    public Map<String, Object> operationalSummary() {
        List<Map<String, Object>> jobs = jdbc.queryForList(
                "select id, job_type, ref_id, source_event_id, status, attempts, max_attempts, last_error, next_attempt_at, updated_at from job order by created_at desc limit 100");
        List<Map<String, Object>> outbox = jdbc.queryForList(
                "select id, event_id, aggregate_type, event_type, attempts, last_error, next_attempt_at, created_at, published_at from outbox order by created_at desc limit 100");
        List<Map<String, Object>> reassessments = listReassessments();
        return Map.of("jobs", jobs, "outbox", outbox, "reassessments", reassessments);
    }

    // ==================== utilitários ====================

    static boolean isRedistributable(String license) {
        return license != null && REDISTRIBUTABLE_LICENSES.contains(license.trim().toUpperCase());
    }

    private static String csv(String s) {
        if (s == null) return "\"\"";
        return "\"" + s.replace("\"", "\"\"").replace('\n', ' ').replace('\r', ' ') + "\"";
    }

    private static byte[] buildMinimalPdf(List<String> lines) {
        // Fonte monoespacada: 95 caracteres a 9pt cabem na largura util da pagina A4.
        List<String> wrapped = new ArrayList<>();
        for (String line : lines) {
            for (String paragraph : line.split("\\R", -1)) {
                if (paragraph.isEmpty()) wrapped.add("");
                for (int start = 0; start < paragraph.length(); start += 95) {
                    wrapped.add(paragraph.substring(start, Math.min(start + 95, paragraph.length())));
                }
            }
        }
        int pageCount = Math.max(1, (wrapped.size() + 49) / 50);
        List<byte[]> objects = new ArrayList<>();
        objects.add("<< /Type /Catalog /Pages 2 0 R >>".getBytes(StandardCharsets.US_ASCII));
        StringBuilder kids = new StringBuilder();
        for (int page = 0; page < pageCount; page++) kids.append(4 + page * 2).append(" 0 R ");
        objects.add(("<< /Type /Pages /Kids [" + kids + "] /Count " + pageCount + " >>").getBytes(StandardCharsets.US_ASCII));
        objects.add("<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>".getBytes(StandardCharsets.US_ASCII));
        for (int page = 0; page < pageCount; page++) {
            int contentId = 5 + page * 2;
            objects.add(("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 3 0 R >> >> /Contents "
                    + contentId + " 0 R >>").getBytes(StandardCharsets.US_ASCII));
            StringBuilder stream = new StringBuilder("BT\n/F1 9 Tf\n40 790 Td\n14 TL\n");
            for (int i = page * 50; i < Math.min((page + 1) * 50, wrapped.size()); i++) {
                String safe = wrapped.get(i).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)");
                stream.append('(').append(safe).append(") Tj T*\n");
            }
            stream.append("ET\nBT /F1 9 Tf 40 35 Td (Pagina ").append(page + 1).append(" de ").append(pageCount).append(") Tj ET\n");
            byte[] content = stream.toString().getBytes(java.nio.charset.Charset.forName("windows-1252"));
            ByteArrayOutputStream object = new ByteArrayOutputStream();
            writeAscii(object, "<< /Length " + content.length + " >>\nstream\n");
            object.writeBytes(content);
            writeAscii(object, "endstream");
            objects.add(object.toByteArray());
        }
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        writeAscii(out, "%PDF-1.4\n");
        List<Integer> offsets = new ArrayList<>();
        for (int i = 0; i < objects.size(); i++) {
            offsets.add(out.size());
            writeAscii(out, (i + 1) + " 0 obj\n");
            out.writeBytes(objects.get(i));
            writeAscii(out, "\nendobj\n");
        }
        int xref = out.size();
        int size = objects.size() + 1;
        writeAscii(out, "xref\n0 " + size + "\n0000000000 65535 f \n");
        for (int offset : offsets) writeAscii(out, String.format(java.util.Locale.ROOT, "%010d 00000 n \n", offset));
        writeAscii(out, "trailer << /Size " + size + " /Root 1 0 R >>\nstartxref\n" + xref + "\n%%EOF\n");
        return out.toByteArray();
    }

    private static void writeAscii(ByteArrayOutputStream out, String s) {
        out.writeBytes(s.getBytes(StandardCharsets.ISO_8859_1));
    }

    private String write(Object o) {
        try {
            return om.writeValueAsString(o);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException(e);
        }
    }

    private JsonNode read(String s) {
        try {
            return om.readTree(s);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException(e);
        }
    }
}
