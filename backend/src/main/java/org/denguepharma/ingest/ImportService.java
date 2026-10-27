package org.denguepharma.ingest;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.LocalDate;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.UUID;
import org.denguepharma.audit.AuditService;
import org.denguepharma.ingest.SourceConnector.Identifier;
import org.denguepharma.ingest.SourceConnector.Page;
import org.denguepharma.ingest.SourceConnector.RawRecord;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.web.server.ResponseStatusException;

/**
 * RF-02: importa e atualiza registros com checkpoint. Repetir a coleta não duplica documentos nem estudos.
 * A chamada HTTP nunca ocorre dentro de transação; cada página é persistida atomicamente junto com o checkpoint.
 */
@Service
public class ImportService {

    public enum Outcome { NEW, UPDATED, UNCHANGED }

    private static final Logger log = LoggerFactory.getLogger(ImportService.class);

    private final JdbcTemplate jdbc;
    private final TransactionTemplate tx;
    private final ObjectMapper om;
    private final AuditService audit;
    private final Map<String, SourceConnector> connectors;

    public ImportService(JdbcTemplate jdbc, PlatformTransactionManager tm, ObjectMapper om, AuditService audit,
                         List<SourceConnector> connectors) {
        this.jdbc = jdbc;
        this.tx = new TransactionTemplate(tm);
        this.om = om;
        this.audit = audit;
        this.connectors = new TreeMap<>();
        connectors.forEach(c -> this.connectors.put(c.source(), c));
    }

    /** Execuções interrompidas por queda do processo ficam retomáveis. */
    @EventListener(ApplicationReadyEvent.class)
    public void recoverInterrupted() {
        int n = jdbc.update("update search_run set status = 'FAILED', last_error = 'interrompida (processo encerrado)'"
                + " where status = 'RUNNING'");
        if (n > 0) log.warn("{} importacao(oes) interrompida(s) marcada(s) como retomavel(is)", n);
    }

    public UUID start(UUID protocolId, String source, UUID requestedBy) {
        SourceConnector connector = connectors.get(source);
        if (connector == null) {
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, "fonte desconhecida: " + source);
        }
        Map<String, Object> p = jdbc.query("select status, strategy::text as strategy, cutoff_date, sources::text as sources"
                        + " from protocol where id = ?",
                rs -> rs.next() ? Map.<String, Object>of("status", rs.getString("status"), "strategy", rs.getString("strategy"),
                        "cutoff", rs.getObject("cutoff_date", LocalDate.class), "sources", rs.getString("sources")) : null,
                protocolId);
        if (p == null) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "protocolo nao encontrado");
        if ("DRAFT".equals(p.get("status"))) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "registre o protocolo antes de importar");
        }
        JsonNode strategy = readTree((String) p.get("strategy"));
        if (!readTree((String) p.get("sources")).toString().contains("\"" + source + "\"")) {
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, "fonte nao prevista no protocolo");
        }
        UUID runId = UUID.randomUUID();
        jdbc.update("insert into search_run (id, protocol_id, source, query, connector_version, requested_by)"
                        + " values (?, ?, ?, ?, ?, ?)", runId, protocolId, source,
                connector.describeQuery(strategy, (LocalDate) p.get("cutoff")), connector.connectorVersion(), requestedBy);
        audit.record(requestedBy, "IMPORT_STARTED", "search_run", runId.toString(), null,
                "{\"source\":\"" + source + "\"}", null);
        return runId;
    }

    /** Retoma uma importação que falhou, a partir do último checkpoint persistido. */
    public void resumeMarker(UUID runId) {
        int n = jdbc.update("update search_run set status = 'RUNNING', last_error = null where id = ? and status = 'FAILED'", runId);
        if (n == 0) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "somente importacoes com falha podem ser retomadas");
        }
    }

    public void execute(UUID runId) {
        try {
            Map<String, Object> run = jdbc.queryForMap("""
                    select sr.source, sr.checkpoint::text as checkpoint, p.strategy::text as strategy, p.cutoff_date
                    from search_run sr join protocol p on p.id = sr.protocol_id where sr.id = ?
                    """, runId);
            SourceConnector connector = connectors.get((String) run.get("source"));
            JsonNode strategy = readTree((String) run.get("strategy"));
            LocalDate cutoff = ((java.sql.Date) run.get("cutoff_date")).toLocalDate();
            JsonNode checkpoint = run.get("checkpoint") == null ? null : readTree((String) run.get("checkpoint"));

            while (true) {
                final JsonNode checkpointIn = checkpoint;
                Page page = connector.fetch(strategy, cutoff, checkpointIn);   // fora de transação
                tx.executeWithoutResult(st -> persistPage(runId, page, checkpointIn));
                if (page.nextCheckpoint() == null) {
                    return;
                }
                checkpoint = page.nextCheckpoint();
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            markFailed(runId, "interrompida");
        } catch (Exception e) {
            log.warn("importacao {} falhou: {}", runId, e.getMessage());
            markFailed(runId, e.getMessage());
        }
    }

    private void markFailed(UUID runId, String message) {
        jdbc.update("update search_run set status = 'FAILED', last_error = ? where id = ?",
                message == null ? "erro desconhecido" : message, runId);
    }

    private void persistPage(UUID runId, Page page, JsonNode checkpointIn) {
        int created = 0, updated = 0, unchanged = 0;
        for (RawRecord r : page.records()) {
            switch (processRecord(runId, r)) {
                case NEW -> created++;
                case UPDATED -> updated++;
                case UNCHANGED -> unchanged++;
            }
        }
        ObjectNode entry = om.createObjectNode();
        entry.set("checkpoint_in", checkpointIn);
        entry.set("params", om.valueToTree(page.params()));
        entry.put("returned", page.records().size());
        entry.put("at", java.time.Instant.now().toString());
        boolean done = page.nextCheckpoint() == null;

        jdbc.update("""
                update search_run set
                    checkpoint = ?::jsonb,
                    params = case when params = '{}'::jsonb then ?::jsonb else params end,
                    pagination = jsonb_set(pagination, '{pages}', coalesce(pagination->'pages', '[]'::jsonb) || ?::jsonb),
                    api_version = coalesce(api_version, ?),
                    total_returned = coalesce(?, total_returned),
                    records_seen = records_seen + ?, records_created = records_created + ?,
                    records_updated = records_updated + ?, records_unchanged = records_unchanged + ?,
                    status = case when ? then 'COMPLETED' else status end,
                    finished_at = case when ? then now() else finished_at end
                where id = ?
                """,
                done ? null : write(page.nextCheckpoint()), write(page.params()), write(entry), page.apiVersion(),
                page.total(), page.records().size(), created, updated, unchanged, done, done, runId);
    }

    /** Insere ou versiona um registro. Identidade por identificador externo único por fonte e tipo. */
    Outcome processRecord(UUID runId, RawRecord r) {
        JsonNode canonical = canonical(r.payload());
        String hash = sha256(write(canonical));

        UUID studyId = findStudy(r.source(), r.idType(), r.externalId());
        boolean newStudy = studyId == null;
        if (newStudy) {
            studyId = jdbc.queryForObject("insert into study (title) values (?) returning id", UUID.class, r.title());
            jdbc.update("insert into study_identifier (study_id, source, id_type, value) values (?, ?, ?, ?)",
                    studyId, r.source(), r.idType(), r.externalId());
            for (Identifier id : r.secondary()) {
                int n = jdbc.update("insert into study_identifier (study_id, source, id_type, value) values (?, ?, ?, ?)"
                        + " on conflict (source, id_type, value) do nothing", studyId, id.source(), id.idType(), id.value());
                if (n == 0) {
                    // Mesmo DOI/PMCID já ligado a outro estudo: possível relato do mesmo ensaio. Não funde sozinho (T3).
                    UUID existingStudyId = findStudy(id.source(), id.idType(), id.value());
                    if (existingStudyId != null && !existingStudyId.equals(studyId)) {
                        jdbc.update("""
                                insert into study_link_proposal (primary_study_id, candidate_study_id, shared_identifier, id_type, reason)
                                values (?, ?, ?, ?, ?)
                                """, existingStudyId, studyId, id.value(), id.idType(),
                                "Identificador compartilhado detectado na importacao (" + r.source() + ": " + r.externalId() + ")");
                    }
                    audit.record(null, "IDENTIFIER_CONFLICT", "study", studyId.toString(), null,
                            write(Map.of("identifier", id.value(), "type", id.idType(), "record", r.externalId())),
                            "revisar vinculo entre estudos");
                }
            }
        }

        List<Map<String, Object>> latest = jdbc.queryForList("""
                select dv.id, dv.document_id, dv.version_no, dv.content_hash
                from document_version dv join study_document sd on sd.document_id = dv.document_id
                where sd.study_id = ? and dv.origin = ? order by dv.version_no desc limit 1
                """, studyId, r.source());

        if (latest.isEmpty()) {
            UUID documentId = jdbc.queryForObject("insert into document (doc_type, title) values (?, ?) returning id",
                    UUID.class, r.docType(), r.title());
            UUID versionId = insertVersion(documentId, 1, hash, r, canonical);
            jdbc.update("insert into study_document (study_id, document_id, report_role, link_certainty)"
                            + " values (?, ?, ?, 'CONFIRMADO')", studyId, documentId,
                    "REGISTRO_ENSAIO".equals(r.docType()) ? "REGISTRO" : "PUBLICACAO_PRINCIPAL");
            outbox("DocumentoImportado", versionId, documentId, studyId, r, hash);
            return Outcome.NEW;
        }

        Map<String, Object> last = latest.get(0);
        if (hash.equals(last.get("content_hash"))) {
            return Outcome.UNCHANGED;
        }
        boolean hashSeenBefore = Boolean.TRUE.equals(jdbc.queryForObject(
                "select exists (select 1 from document_version where content_hash = ? and origin = ?)",
                Boolean.class, hash, r.source()));
        if (hashSeenBefore) {
            // Conteúdo voltou a uma versão anterior: a unicidade por hash/origem impede nova linha.
            audit.record(null, "SOURCE_REVERTED", "document", last.get("document_id").toString(), null,
                    write(Map.of("record", r.externalId())), "conteudo igual a versao anterior nao vigente");
            return Outcome.UNCHANGED;
        }
        UUID documentId = (UUID) last.get("document_id");
        int nextVersion = ((Number) last.get("version_no")).intValue() + 1;
        UUID versionId = insertVersion(documentId, nextVersion, hash, r, canonical);
        jdbc.update("""
                insert into reassessment_task (study_id, document_version_id, trigger_type, notes)
                values (?, ?, 'FONTE_ALTERADA', ?)
                """, studyId, versionId, "Nova versao v" + nextVersion + " detectada em " + r.source());
        outbox("FonteAlterada", versionId, documentId, studyId, r, hash);
        return Outcome.UPDATED;
    }

    private UUID insertVersion(UUID documentId, int versionNo, String hash, RawRecord r, JsonNode canonical) {
        return jdbc.queryForObject("""
                insert into document_version (document_id, version_no, content_hash, origin, access_status, retrieved_at, metadata)
                values (?, ?, ?, ?, ?, now(), ?::jsonb) returning id
                """, UUID.class, documentId, versionNo, hash, r.source(), r.accessStatus(), write(canonical));
    }

    /** Evento na mesma transação da mutação; só referências, nunca o texto integral. */
    private void outbox(String type, UUID versionId, UUID documentId, UUID studyId, RawRecord r, String hash) {
        ObjectNode payload = om.createObjectNode();
        payload.put("document_version_id", versionId.toString());
        payload.put("document_id", documentId.toString());
        payload.put("study_id", studyId.toString());
        payload.put("source", r.source());
        payload.put("external_id", r.externalId());
        payload.put("content_hash", hash);
        jdbc.update("insert into outbox (event_id, aggregate_type, aggregate_id, event_type, payload) values (?, ?, ?, ?, ?::jsonb)",
                UUID.randomUUID(), "document_version", versionId.toString(), type, write(payload));
    }

    private UUID findStudy(String source, String idType, String value) {
        List<UUID> ids = jdbc.queryForList("select study_id from study_identifier where source = ? and id_type = ? and value = ?",
                UUID.class, source, idType, value);
        return ids.isEmpty() ? null : ids.get(0);
    }

    // ---- util ----

    static JsonNode canonical(JsonNode n) {
        if (n.isObject()) {
            ObjectNode out = JsonNodeFactoryHolder.FACTORY.objectNode();
            new TreeMap<String, JsonNode>(toMap(n)).forEach((k, v) -> out.set(k, canonical(v)));
            return out;
        }
        if (n.isArray()) {
            ArrayNode out = JsonNodeFactoryHolder.FACTORY.arrayNode();
            n.forEach(e -> out.add(canonical(e)));
            return out;
        }
        return n;
    }

    private static Map<String, JsonNode> toMap(JsonNode obj) {
        Map<String, JsonNode> m = new java.util.HashMap<>();
        obj.fields().forEachRemaining(e -> m.put(e.getKey(), e.getValue()));
        return m;
    }

    private static final class JsonNodeFactoryHolder {
        static final com.fasterxml.jackson.databind.node.JsonNodeFactory FACTORY =
                com.fasterxml.jackson.databind.node.JsonNodeFactory.instance;
    }

    static String sha256(String s) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(s.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    private String write(Object o) {
        try {
            return om.writeValueAsString(o);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException(e);
        }
    }

    private JsonNode readTree(String s) {
        try {
            return om.readTree(s);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException(e);
        }
    }
}

