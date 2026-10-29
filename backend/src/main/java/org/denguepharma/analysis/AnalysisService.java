package org.denguepharma.analysis;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.*;
import java.util.zip.ZipInputStream;
import org.denguepharma.audit.AuditService;
import org.denguepharma.catalog.CatalogService.CatalogFilter;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class AnalysisService {
    public static final String DICTIONARY = "descriptive-v2.0";
    public static final List<String> FIELDS = List.of("substance", "design", "phase", "serotype", "outcome_category");
    private static final int MAX_BYTES = 32 * 1024 * 1024;
    private final JdbcTemplate jdbc;
    private final ObjectMapper json;
    private final AuditService audit;
    public AnalysisService(JdbcTemplate jdbc, ObjectMapper json, AuditService audit) {
        this.jdbc = jdbc; this.json = json; this.audit = audit;
    }

    @Transactional(isolation = Isolation.REPEATABLE_READ)
    public Map<String, Object> create(CatalogFilter filter, UUID actor) {
        UUID snapshot = UUID.randomUUID(), run = UUID.randomUUID(), event = UUID.randomUUID();
        var studies = reviewedStudies(filter);
        var dataset = new LinkedHashMap<String, Object>();
        dataset.put("schemaVersion", "2.0"); dataset.put("dictionaryVersion", DICTIONARY);
        dataset.put("snapshotId", snapshot); dataset.put("createdAt", Instant.now().toString());
        dataset.put("filters", filter); dataset.put("fields", FIELDS); dataset.put("studies", studies);
        String content = write(dataset), hash = sha256(content.getBytes(StandardCharsets.UTF_8));
        jdbc.update("""
                insert into analysis_snapshot(id, requested_by, filters, dictionary_version, dataset, canonical_content, content_hash)
                values(?,?,?::jsonb,?,?::jsonb,?,?)
                """, snapshot, actor, write(filter), DICTIONARY, content, content, hash);
        jdbc.update("""
                insert into outbox(event_id,aggregate_type,aggregate_id,event_type,payload)
                values(?,'analysis_run',?,'AnaliseSolicitada',?::jsonb)
                """, event, run.toString(), write(Map.of("snapshotId", snapshot, "analysisId", run)));
        jdbc.update("insert into analysis_run(id,snapshot_id,source_event_id) values(?,?,?)", run, snapshot, event);
        audit.record(actor, "ANALYSIS_REQUESTED", "analysis_run", run.toString(), null, write(Map.of("inputHash", hash, "studies", studies.size())), null);
        return get(run);
    }

    List<Map<String, Object>> reviewedStudies(CatalogFilter filter) {
        var rows = jdbc.queryForList("""
                select s.id, s.title, s.context, s.purpose,
                    exists(select 1 from reassessment_task rt where rt.study_id = s.id and rt.status = 'PENDING') as reassessment_pending
                from study s where s.status = 'ATIVO' and not s.is_demo and s.merged_into_id is null
                  and s.screening_status in ('INCLUIDO_NUCLEO','INCLUIDO_SEM_RESULTADO','CAMADA_COMPLEMENTAR')
                  and exists(select 1 from extracted_field ef where ef.study_id = s.id and ef.published and ef.review_status = 'APROVADO')
                order by s.id
                """);
        List<Map<String, Object>> studies = new ArrayList<>();
        for (var row : rows) {
            UUID study = (UUID) row.get("id");
            var annotations = jdbc.queryForList("""
                    select ef.id, ef.field_name, ef.normalized_value, ef.absence_status,
                        dv.id as document_version_id, dv.document_id, dv.origin, dv.content_hash,
                        es.locator, es.document_version_id as span_version_id,
                        exists(select 1 from study_identifier si where si.study_id = ef.study_id) as has_identifier
                    from extracted_field ef join extraction_run er on er.id = ef.extraction_run_id
                    join document_version dv on dv.id = er.document_version_id
                    left join evidence_span es on es.id = ef.evidence_span_id
                    where ef.study_id = ? and ef.published and ef.review_status = 'APROVADO'
                    order by ef.id
                    """, study);
            Map<String, List<Map<String, Object>>> grouped = new TreeMap<>();
            List<Map<String, Object>> references = new ArrayList<>();
            for (var annotation : annotations) {
                String field = canonicalField((String) annotation.get("field_name"));
                if (!FIELDS.contains(field)) continue;
                grouped.computeIfAbsent(field, k -> new ArrayList<>()).add(annotation);
                var ref = new LinkedHashMap<String, Object>();
                ref.put("field", field); ref.put("fieldId", annotation.get("id"));
                ref.put("documentVersionId", annotation.get("document_version_id"));
                ref.put("documentId", annotation.get("document_id")); ref.put("source", annotation.get("origin"));
                ref.put("contentHash", annotation.get("content_hash")); ref.put("locator", annotation.get("locator"));
                ref.put("absenceStatus", annotation.get("absence_status"));
                ref.put("hasIdentifier", annotation.get("has_identifier"));
                ref.put("hasVersion", annotation.get("document_version_id") != null && annotation.get("content_hash") != null
                        && ((String) annotation.get("content_hash")).matches("[a-fA-F0-9]{64}"));
                ref.put("hasLocator", annotation.get("locator") != null && !((String) annotation.get("locator")).isBlank()
                        && Objects.equals(annotation.get("span_version_id"), annotation.get("document_version_id")));
                references.add(ref);
            }
            Map<String, Object> fields = new LinkedHashMap<>();
            for (String field : FIELDS) fields.put(field, resolve(grouped.getOrDefault(field, List.of())));
            var item = new LinkedHashMap<String, Object>();
            item.put("studyId", study); item.put("title", row.get("title"));
            item.put("context", row.get("context")); item.put("purpose", row.get("purpose"));
            item.put("reassessmentPending", row.get("reassessment_pending"));
            item.put("fields", fields); item.put("references", references);
            item.put("screeningDecisionIds", jdbc.queryForList("select id from screening_decision where study_id = ? order by id", UUID.class, study));
            if (matches(item, fields, filter)) studies.add(item);
        }
        return studies;
    }

    private String canonicalField(String field) {
        return Set.of("substance_name", "substance_published_name").contains(field) ? "substance" : field;
    }
    private Map<String, Object> resolve(List<Map<String, Object>> annotations) {
        if (annotations.isEmpty()) return Map.of("status", "SEM_REVISAO");
        Map<String, Map<String, Object>> distinct = new TreeMap<>();
        for (var annotation : annotations) {
            String status = (String) annotation.get("absence_status");
            String value = (String) annotation.get("normalized_value");
            if ("PRESENTE".equals(status) && (value == null || value.isBlank())) status = "INCERTO";
            var candidate = new LinkedHashMap<String, Object>(); candidate.put("status", status);
            if ("PRESENTE".equals(status)) candidate.put("value", value.trim());
            distinct.putIfAbsent(status + ":" + ("PRESENTE".equals(status) ? value.trim().toLowerCase(Locale.ROOT) : ""), candidate);
        }
        if (distinct.size() > 1) return Map.of("status", "CONFLITO", "alternatives", distinct.values());
        return distinct.values().iterator().next();
    }
    private boolean matches(Map<String, Object> study, Map<String, Object> fields, CatalogFilter f) {
        if (!match(study.get("context"), f.context(), false) || !match(study.get("purpose"), f.purpose(), false)) return false;
        return match(value(fields, "substance"), f.substance(), true) && match(value(fields, "design"), f.design(), false)
                && match(value(fields, "phase"), f.phase(), false) && match(value(fields, "serotype"), f.serotype(), true);
    }
    private Object value(Map<String, Object> fields, String field) { return ((Map<?, ?>) fields.get(field)).get("value"); }
    private boolean match(Object value, String filter, boolean contains) {
        if (filter == null || filter.isBlank()) return true;
        if (value == null) return false;
        String v = value.toString().toLowerCase(Locale.ROOT), f = filter.trim().toLowerCase(Locale.ROOT);
        return contains ? v.contains(f) : v.equals(f);
    }

    public List<Map<String, Object>> list() {
        return jdbc.queryForList("""
                select a.id, a.snapshot_id, a.created_at, s.content_hash as input_hash, s.dictionary_version, exists(select 1 from analysis_publication p where p.analysis_id=a.id) as published, s.filters::text as filters,
                    jsonb_array_length(s.dataset->'studies') as study_count, coalesce(j.status,'PENDING') as status, j.last_error
                from analysis_run a join analysis_snapshot s on s.id = a.snapshot_id
                left join job j on j.source_event_id = a.source_event_id order by a.created_at desc limit 200
                """);
    }
    public Map<String, Object> get(UUID id) {
        var rows = jdbc.queryForList("""
                select a.id, a.snapshot_id, a.created_at, s.content_hash as input_hash, s.dictionary_version,
                    s.filters::text as filters, jsonb_array_length(s.dataset->'studies') as study_count,
                    coalesce(j.status,'PENDING') as status, j.last_error
                from analysis_run a join analysis_snapshot s on s.id=a.snapshot_id
                left join job j on j.source_event_id=a.source_event_id where a.id=?
                """, id);
        if (rows.isEmpty()) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "analise nao encontrada");
        var result = rows.get(0);
        result.put("artifacts", jdbc.queryForList("select name,media_type,content_hash,octet_length(content) as size_bytes from analysis_artifact where analysis_id=? order by name", id));
        return result;
    }
    public Map<String, Object> input(UUID id) {
        var rows = jdbc.queryForList("select s.canonical_content as content, s.content_hash from analysis_run a join analysis_snapshot s on s.id=a.snapshot_id where a.id=?", id);
        if (rows.isEmpty()) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "analise nao encontrada");
        return rows.get(0);
    }
    public record File(byte[] content, String mediaType) {}
    public File artifact(UUID id, String name) {
        // A entrada ja esta congelada: permite reproducao por CLI mesmo sem worker ativo.
        if ("dataset.json".equals(name)) return new File(((String) input(id).get("content")).getBytes(StandardCharsets.UTF_8), "application/json");
        var rows = jdbc.queryForList("select content,media_type from analysis_artifact where analysis_id=? and name=?", id, name);
        if (rows.isEmpty()) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "artefato indisponivel");
        return new File((byte[]) rows.get(0).get("content"), (String) rows.get(0).get("media_type"));
    }

    /** Chamado na transacao de conclusao do job; nada parcial fica visivel. */
    @Transactional
    public void persist(UUID id, byte[] zip) {
        if (zip.length > MAX_BYTES) invalid("pacote excede limite de 32 MiB");
        Map<String, byte[]> files = new TreeMap<>();
        int total = 0;
        try (var stream = new ZipInputStream(new ByteArrayInputStream(zip), StandardCharsets.UTF_8)) {
            java.util.zip.ZipEntry entry;
            while ((entry = stream.getNextEntry()) != null) {
                String name = entry.getName();
                if (!name.matches("[a-z0-9_./-]{1,128}") || name.contains("..") || name.startsWith("/") || entry.isDirectory()
                        || files.size() >= 256 || files.containsKey(name) || !(name.endsWith(".csv") || name.endsWith(".json") || name.endsWith(".html") || name.matches("figures/[a-z0-9_-]+\\.png"))) invalid("nome de artefato invalido");
                byte[] content = stream.readNBytes(MAX_BYTES - total + 1); total += content.length;
                if (total > MAX_BYTES) invalid("conteudo descompactado excede limite");
                files.put(name, content);
            }
        } catch (IOException | IllegalArgumentException e) { invalid("ZIP invalido"); }
        if (!files.keySet().containsAll(Set.of("dataset.json", "dataset.csv", "distributions.csv", "completeness.csv", "gaps.csv", "traceability.csv", "summary.json", "manifest.json", "report.html"))) invalid("pacote incompleto");
        JsonNode manifest = read(files.get("manifest.json")), summary = read(files.get("summary.json"));
        var input = input(id);
        JsonNode snapshot = read(((String) input.get("content")).getBytes(StandardCharsets.UTF_8));
        if ("3.0".equals(snapshot.path("schemaVersion").asText()) && !files.keySet().containsAll(Set.of(
                "records.json","documents.csv","studies.csv","evidence_fields.csv","temporal.csv","enrollment.csv","links.csv","link_candidates.csv","pilot_review.csv","reproduction_source.json"))) invalid("pacote de corpus incompleto");
        if (!input.get("content_hash").equals(manifest.path("inputHash").asText()) || !snapshot.path("dictionaryVersion").asText().equals(manifest.path("dictionaryVersion").asText())
                || manifest.path("scriptVersion").asText().isBlank() || !snapshot.path("schemaVersion").asText().equals(summary.path("schemaVersion").asText())) invalid("manifesto incompativel com snapshot");
        if (!Arrays.equals(((String) input.get("content")).getBytes(StandardCharsets.UTF_8), files.get("dataset.json"))) invalid("dataset nao corresponde ao snapshot");
        if (read(files.get("dataset.json")).path("studies").size() > 0 && files.keySet().stream().noneMatch(name -> name.startsWith("figures/") && name.endsWith(".png"))) invalid("analise sem graficos");
        if (!manifest.path("dependencies").isObject() || !manifest.path("scriptHash").asText().matches("[a-f0-9]{64}")) invalid("versoes de reproducao ausentes");
        var hashes = manifest.path("artifacts");
        for (var entry : files.entrySet()) {
            if (!entry.getKey().equals("manifest.json") && !sha256(entry.getValue()).equals(hashes.path(entry.getKey()).asText())) invalid("hash de artefato divergente");
        }
        files.put("bundle.zip", zip);
        for (var entry : files.entrySet()) {
            String hash = sha256(entry.getValue()), name = entry.getKey();
            jdbc.update("insert into analysis_artifact(analysis_id,name,media_type,content_hash,storage_uri,content) values(?,?,?,?,?,?)",
                    id, name, mediaType(name), hash, "s3://denguepharma-corpus/analyses/" + id + "/" + hash + "/" + name, entry.getValue());
        }
    }
    private String mediaType(String name) {
        if (name.endsWith(".png")) return "image/png";
        if (name.endsWith(".csv")) return "text/csv;charset=UTF-8";
        if (name.endsWith(".html")) return "text/html;charset=UTF-8";
        return name.endsWith(".zip") ? "application/zip" : "application/json";
    }
    private void invalid(String message) { throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, message); }
    private JsonNode read(byte[] bytes) {
        try { JsonNode node=json.readTree(bytes); if (node == null || !node.isObject()) invalid("JSON invalido no pacote"); return node; }
        catch (IOException e) { invalid("JSON invalido no pacote"); return null; }
    }
    private String write(Object value) { try { return json.writeValueAsString(value); } catch (JsonProcessingException e) { throw new IllegalStateException(e); } }
    public static String sha256(byte[] bytes) { try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes)); } catch (java.security.NoSuchAlgorithmException e) { throw new IllegalStateException(e); } }
}
