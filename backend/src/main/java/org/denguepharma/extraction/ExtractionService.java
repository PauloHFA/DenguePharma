package org.denguepharma.extraction;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.denguepharma.audit.AuditService;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

/**
 * RF-05, RF-06, Seção 10 e Cenários T4, T5, T7, T10:
 * Extração estruturada com validação determinística de schema, números/denominadores e trecho literal,
 * abstenção explícita quando faltar suporte, proteção contra prompt injection e revisão humana lado a lado.
 */
@Service
public class ExtractionService {

    public static final Set<String> ABSENCE_STATUSES = Set.of(
            "PRESENTE", "NAO_INFORMADO", "NAO_APLICAVEL", "NAO_EXTRAIDO", "INCERTO", "NAO_HOUVE_EVENTO");

    public static final Set<String> CRITICAL_FIELDS = Set.of(
            "purpose", "population", "design", "intervention", "comparator",
            "outcome", "time_frame", "sample_size", "result");

    private static final Pattern PROMPT_INJECTION_PATTERN = Pattern.compile(
            "(?i)(ignore\\s+(all\\s+)?(previous|prior)\\s+instructions|system\\s+override|<script\\b|drop\\s+table|rm\\s+-rf|curl\\s+http|exec\\()");

    // Detecta fração "X/Y" ou "X de Y" ou "X of Y" para validar numerador <= denominador (T5).
    private static final Pattern FRACTION_PATTERN = Pattern.compile("(\\d+)\\s*(?:/|de|of)\\s*(\\d+)");
    private static final Pattern PERCENT_PATTERN = Pattern.compile("(-?\\d+(?:[.,]\\d+)?)\\s*%");
    private static final Pattern MEDIAN_TO_MEAN_PATTERN = Pattern.compile("(?i)mediana.*convertid[ao].*m[eé]dia|median\\s+converted\\s+to\\s+mean");

    public record ProposedField(String fieldName, String originalValue, String normalizedValue,
                                String absenceStatus, String section, Integer page,
                                String locator, String quotedText, Integer denominator) {}

    public record RunInput(UUID documentVersionId, String pipelineVersion, String modelProvider,
                           String modelVersion, String promptHash, String executionVariant,
                           String schemaVersion, List<ProposedField> fields) {}

    public record ReviewInput(UUID extractedFieldId, String decision, String correctedValue,
                              String correctedAbsenceStatus, String reason, boolean adjudication,
                              boolean publishAfterApproval) {}

    private final JdbcTemplate jdbc;
    private final ObjectMapper om;
    private final AuditService audit;

    public ExtractionService(JdbcTemplate jdbc, ObjectMapper om, AuditService audit) {
        this.jdbc = jdbc;
        this.om = om;
        this.audit = audit;
    }

    /**
     * Registra uma execução de extração de forma idempotente (T7): se já existir execução com a mesma
     * chave lógica (document_version_id + pipeline_version + model_version + prompt_hash + execution_variant),
     * retorna a execução existente sem duplicar campos.
     */
    @Transactional
    public Map<String, Object> submitExtraction(RunInput in, UUID actor) {
        String variant = (in.executionVariant() == null || in.executionVariant().isBlank())
                ? "default" : in.executionVariant();

        List<UUID> existing = jdbc.queryForList("""
                select id from extraction_run
                where document_version_id = ? and pipeline_version = ? and model_version = ?
                  and prompt_hash = ? and execution_variant = ?
                """, UUID.class, in.documentVersionId(), in.pipelineVersion(),
                in.modelVersion(), in.promptHash(), variant);

        if (!existing.isEmpty()) {
            return Map.of("extractionRunId", existing.get(0), "idempotentReplay", true);
        }

        List<Map<String, Object>> dvRows = jdbc.queryForList("""
                select dv.id, dv.metadata::text as metadata, sd.study_id
                from document_version dv
                left join study_document sd on sd.document_id = dv.document_id
                where dv.id = ?
                """, in.documentVersionId());
        if (dvRows.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "versao de documento nao encontrada");
        }
        String documentCorpus = String.valueOf(dvRows.get(0).get("metadata"));
        UUID studyId = (UUID) dvRows.get(0).get("study_id");

        UUID runId = UUID.randomUUID();
        try {
            jdbc.update("""
                    insert into extraction_run (id, document_version_id, pipeline_version, model_provider,
                                                model_version, prompt_hash, execution_variant, schema_version, status, attempts)
                    values (?, ?, ?, ?, ?, ?, ?, ?, 'COMPLETED', 1)
                    """, runId, in.documentVersionId(), in.pipelineVersion(), in.modelProvider(),
                    in.modelVersion(), in.promptHash(), variant, in.schemaVersion());
        } catch (DuplicateKeyException e) {
            UUID winner = jdbc.queryForObject("""
                    select id from extraction_run
                    where document_version_id = ? and pipeline_version = ? and model_version = ?
                      and prompt_hash = ? and execution_variant = ?
                    """, UUID.class, in.documentVersionId(), in.pipelineVersion(),
                    in.modelVersion(), in.promptHash(), variant);
            return Map.of("extractionRunId", winner, "idempotentReplay", true);
        }

        int acceptedDrafts = 0;
        int abstainedOrBlocked = 0;
        List<String> validationWarnings = new ArrayList<>();

        for (ProposedField f : in.fields() == null ? List.<ProposedField>of() : in.fields()) {
            if (f.fieldName() == null || f.fieldName().isBlank()) {
                throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, "fieldName obrigatorio no schema");
            }
            String status = (f.absenceStatus() == null || f.absenceStatus().isBlank())
                    ? "PRESENTE" : f.absenceStatus();
            if (!ABSENCE_STATUSES.contains(status)) {
                throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, "absenceStatus invalido: " + status);
            }

            String origVal = sanitizeDataOnly(f.originalValue(), f.fieldName(), validationWarnings);
            String normVal = sanitizeDataOnly(f.normalizedValue(), f.fieldName(), validationWarnings);
            String quote = sanitizeDataOnly(f.quotedText(), f.fieldName(), validationWarnings);

            // T4: Sem trecho citado suficiente ou trecho que não consta no documento -> força INCERTO e não publica.
            if ("PRESENTE".equals(status)) {
                if (!hasLiteralSupport(documentCorpus, quote) || f.locator() == null || f.locator().isBlank()) {
                    status = "INCERTO";
                    normVal = null;
                    validationWarnings.add(f.fieldName() + ": sem trecho de suporte literal na fonte (abstencao T4)");
                }
            }

            // T5: Validação determinística de números, unidades e denominadores.
            if ("PRESENTE".equals(status)) {
                String numericProblem = validateNumericsAndUnits(f.fieldName(), origVal, normVal, f.denominator());
                if (numericProblem != null) {
                    status = "INCERTO";
                    normVal = null;
                    validationWarnings.add(f.fieldName() + ": bloqueado por validacao numerica/unidade (" + numericProblem + ")");
                }
            }

            UUID spanId = null;
            if ("PRESENTE".equals(status)) {
                spanId = UUID.randomUUID();
                jdbc.update("""
                        insert into evidence_span (id, document_version_id, section, page, locator, text)
                        values (?, ?, ?, ?, ?, ?)
                        """, spanId, in.documentVersionId(), f.section(), f.page(), f.locator(), quote);
                acceptedDrafts++;
            } else {
                abstainedOrBlocked++;
            }

            jdbc.update("""
                    insert into extracted_field (extraction_run_id, study_id, field_name, original_value,
                                                 normalized_value, absence_status, evidence_span_id, review_status, published)
                    values (?, ?, ?, ?, ?, ?, ?, 'RASCUNHO_IA', false)
                    """, runId, studyId, f.fieldName(), origVal, normVal, status, spanId);
        }

        ObjectNode evt = om.createObjectNode();
        evt.put("extraction_run_id", runId.toString());
        evt.put("document_version_id", in.documentVersionId().toString());
        evt.put("accepted_drafts", acceptedDrafts);
        evt.put("abstained_or_blocked", abstainedOrBlocked);
        jdbc.update("""
                insert into outbox (event_id, aggregate_type, aggregate_id, event_type, payload)
                values (?, 'extraction_run', ?, 'ExtracaoConcluida', ?::jsonb)
                """, UUID.randomUUID(), runId.toString(), write(evt));

        audit.record(actor, "EXTRACTION_COMPLETED", "extraction_run", runId.toString(),
                null, write(Map.of("acceptedDrafts", acceptedDrafts, "abstainedOrBlocked", abstainedOrBlocked,
                        "warnings", validationWarnings)), null);

        return Map.of(
                "extractionRunId", runId,
                "idempotentReplay", false,
                "acceptedDrafts", acceptedDrafts,
                "abstainedOrBlocked", abstainedOrBlocked,
                "warnings", validationWarnings);
    }

    /** Lista campos extraídos lado a lado com o trecho de suporte e metadados do documento (RF-06). */
    public List<Map<String, Object>> listFieldsForReview() {
        return jdbc.queryForList("""
                select ef.id, ef.extraction_run_id, ef.study_id, s.title as study_title,
                       ef.field_name, ef.original_value, ef.normalized_value, ef.absence_status,
                       ef.review_status, ef.published, ef.created_at,
                       es.section, es.page, es.locator, es.text as evidence_text,
                       er.model_provider, er.model_version, er.pipeline_version,
                       dv.origin as document_origin, dv.version_no as document_version_no, dv.content_hash
                from extracted_field ef
                join extraction_run er on er.id = ef.extraction_run_id
                join document_version dv on dv.id = er.document_version_id
                left join study s on s.id = ef.study_id
                left join evidence_span es on es.id = ef.evidence_span_id
                order by ef.created_at desc
                """);
    }

    /**
     * RF-06: Revisão humana lado a lado (ACEITAR, CORRIGIR, REJEITAR), registrando antes/depois,
     * responsável, motivo e instante. Somente revisão aprovada pode ser publicada.
     */
    @Transactional
    public Map<String, Object> reviewField(ReviewInput in, UUID reviewerId, boolean hasAdjudicatorRole) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
                select ef.*, er.document_version_id
                from extracted_field ef
                join extraction_run er on er.id = ef.extraction_run_id
                where ef.id = ?
                """, in.extractedFieldId());
        if (rows.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "campo extraido nao encontrado");
        }
        Map<String, Object> ef = rows.get(0);
        String fieldName = (String) ef.get("field_name");
        if (in.adjudication() && !hasAdjudicatorRole) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "apenas ADJUDICADOR pode adjudicar campos");
        }

        String beforeVal = (String) ef.get("normalized_value");
        if (beforeVal == null) beforeVal = (String) ef.get("original_value");
        String currentAbsence = (String) ef.get("absence_status");
        UUID currentSpanId = (UUID) ef.get("evidence_span_id");
        UUID docVersionId = (UUID) ef.get("document_version_id");
        UUID studyId = (UUID) ef.get("study_id");

        String nextReviewStatus;
        String afterVal = beforeVal;
        String nextAbsence = currentAbsence;
        UUID nextSpanId = currentSpanId;
        boolean publish = false;

        switch (in.decision()) {
            case "ACEITAR" -> {
                if ("PRESENTE".equals(currentAbsence)) {
                    String problem = validateNumericsAndUnits(fieldName, (String) ef.get("original_value"), beforeVal, null);
                    if (problem != null) {
                        throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,
                                "campo contem inconsistencia numerica/unidade (" + problem + "); use CORRIGIR");
                    }
                }
                nextReviewStatus = "APROVADO";
                publish = in.publishAfterApproval();
            }
            case "CORRIGIR" -> {
                if (in.reason() == null || in.reason().isBlank()) {
                    throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,
                            "correcao exige motivo justificado (RF-06)");
                }
                afterVal = in.correctedValue();
                nextAbsence = (in.correctedAbsenceStatus() == null || in.correctedAbsenceStatus().isBlank())
                        ? (afterVal != null && !afterVal.isBlank() ? "PRESENTE" : "NAO_INFORMADO")
                        : in.correctedAbsenceStatus();
                if ("PRESENTE".equals(nextAbsence)) {
                    String problem = validateNumericsAndUnits(fieldName, afterVal, afterVal, null);
                    if (problem != null) {
                        throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,
                                "valor corrigido invalido: " + problem);
                    }
                    if (nextSpanId == null) {
                        nextSpanId = UUID.randomUUID();
                        jdbc.update("""
                                insert into evidence_span (id, document_version_id, section, locator, text)
                                values (?, ?, 'REVISAO_HUMANA', 'curadoria', ?)
                                """, nextSpanId, docVersionId, "Corrigido pelo revisor: " + in.reason());
                    }
                }
                nextReviewStatus = "APROVADO";
                publish = in.publishAfterApproval();
            }
            case "REJEITAR" -> {
                nextReviewStatus = "REJEITADO";
                publish = false;
            }
            default -> throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,
                    "decisao invalida: " + in.decision());
        }

        // Se o campo já estava APROVADO, o trigger trg_protect_approved_field impede sobrescrita direta dos valores;
        // nesses casos apenas registramos a decisão ou publicamos se não alterar o valor aprovado.
        if ("APROVADO".equals(ef.get("review_status")) && "CORRIGIR".equals(in.decision())) {
            throw new ResponseStatusException(HttpStatus.CONFLICT,
                    "campo ja aprovado nao pode ser sobrescrito in-place; execute nova revisao/extracao");
        }

        jdbc.update("""
                update extracted_field
                set normalized_value = ?, absence_status = ?, evidence_span_id = ?,
                    review_status = ?, published = ?
                where id = ?
                """, afterVal, nextAbsence, nextSpanId, nextReviewStatus, publish, in.extractedFieldId());

        UUID decisionId = UUID.randomUUID();
        jdbc.update("""
                insert into review_decision (id, extracted_field_id, reviewer_id, decision,
                                             value_before, value_after, reason, is_adjudication)
                values (?, ?, ?, ?, ?, ?, ?, ?)
                """, decisionId, in.extractedFieldId(), reviewerId, in.decision(),
                beforeVal, afterVal, in.reason(), in.adjudication());

        if (publish && studyId != null) {
            syncApprovedFieldToStudyCatalog(studyId, fieldName, afterVal);
            ObjectNode evt = om.createObjectNode();
            evt.put("extracted_field_id", in.extractedFieldId().toString());
            evt.put("study_id", studyId.toString());
            evt.put("field_name", fieldName);
            jdbc.update("""
                    insert into outbox (event_id, aggregate_type, aggregate_id, event_type, payload)
                    values (?, 'extracted_field', ?, 'EvidenciaAprovada', ?::jsonb)
                    """, UUID.randomUUID(), in.extractedFieldId().toString(), write(evt));
        }

        audit.record(reviewerId, "FIELD_REVIEWED", "extracted_field", in.extractedFieldId().toString(),
                "{\"value\":" + quoteJson(beforeVal) + ",\"status\":\"" + ef.get("review_status") + "\"}",
                "{\"value\":" + quoteJson(afterVal) + ",\"status\":\"" + nextReviewStatus + "\",\"published\":" + publish + "}",
                in.reason());

        return Map.of("reviewDecisionId", decisionId, "reviewStatus", nextReviewStatus, "published", publish);
    }

    private void syncApprovedFieldToStudyCatalog(UUID studyId, String fieldName, String value) {
        if (value == null || value.isBlank()) return;
        switch (fieldName) {
            case "design" -> jdbc.update("update study set design = ? where id = ?", value, studyId);
            case "phase" -> jdbc.update("update study set phase = ? where id = ?", value, studyId);
            case "serotype" -> jdbc.update("update study set serotype = ? where id = ?", value, studyId);
            case "countries" -> jdbc.update("update study set countries = ? where id = ?", value, studyId);
            case "comparator" -> jdbc.update("update study set comparator_label = ? where id = ?", value, studyId);
            case "outcome" -> jdbc.update("update study set outcome_summary = ? where id = ?", value, studyId);
            case "time_frame" -> jdbc.update("update study set outcome_time_frame = ? where id = ?", value, studyId);
            case "result" -> jdbc.update("update study set effect_summary = ? where id = ?", value, studyId);
            case "limitations" -> jdbc.update("update study set limitations = ? where id = ?", value, studyId);
            case "sample_size" -> {
                try {
                    int n = Integer.parseInt(value.replaceAll("[^0-9]", ""));
                    jdbc.update("update study set sample_size = ? where id = ?", n, studyId);
                } catch (NumberFormatException ignored) {}
            }
            default -> {}
        }
    }

    static boolean hasLiteralSupport(String corpus, String quote) {
        if (corpus == null || quote == null) return false;
        String cleanQuote = quote.trim();
        if (cleanQuote.length() < 5) return false;
        String normCorpus = corpus.replaceAll("\\s+", " ").toLowerCase();
        String normQuote = cleanQuote.replaceAll("\\s+", " ").toLowerCase();
        return normCorpus.contains(normQuote);
    }

    /**
     * T10: Trata qualquer texto recuperado ou saída do modelo como dado puro, neutralizando tentativas
     * de prompt injection ou scripts embutidos.
     */
    static String sanitizeDataOnly(String input, String fieldName, List<String> warnings) {
        if (input == null) return null;
        Matcher m = PROMPT_INJECTION_PATTERN.matcher(input);
        if (m.find()) {
            warnings.add(fieldName + ": instrucao maliciosa/script neutralizada (T10)");
            return m.replaceAll("[INSTRUCAO_BLOQUEADA]");
        }
        return input.trim();
    }

    /**
     * T5: Valida números, unidades, proporções e denominadores.
     * Retorna descrição do erro quando inválido, ou null quando válido.
     */
    static String validateNumericsAndUnits(String fieldName, String orig, String norm, Integer denominator) {
        String text = (norm != null && !norm.isBlank()) ? norm : orig;
        if (text == null || text.isBlank()) return "valor vazio para campo PRESENTE";
        if ( text.contains("[INSTRUCAO_BLOQUEADA]")) return "conteudo bloqueado por seguranca (T10)";
        if (MEDIAN_TO_MEAN_PATTERN.matcher(text).find()) {
            return "proibido converter mediana em media por inferencia (Secao 08)";
        }

        Matcher frac = FRACTION_PATTERN.matcher(text);
        if (frac.find()) {
            long num = Long.parseLong(frac.group(1));
            long den = Long.parseLong(frac.group(2));
            if (den <= 0) return "denominador zero ou negativo (" + num + "/" + den + ")";
            if (num > den) return "numerador maior que o denominador (" + num + "/" + den + ")";
        }

        Matcher pct = PERCENT_PATTERN.matcher(text);
        while (pct.find()) {
            double v = Double.parseDouble(pct.group(1).replace(',', '.'));
            if (v < 0.0 || v > 100.0) {
                return "percentual fora do intervalo 0..100% (" + v + "%)";
            }
        }

        if ("sample_size".equals(fieldName) || "n_analyzed".equals(fieldName)) {
            try {
                int val = Integer.parseInt(text.replaceAll("[^0-9-]", ""));
                if (val <= 0) return "tamanho amostral deve ser positivo";
                if (denominator != null && val > denominator) {
                    return "amostra analisada (" + val + ") maior que denominador randomizado (" + denominator + ")";
                }
            } catch (NumberFormatException e) {
                return "tamanho amostral nao numerico";
            }
        }

        if ("p_value".equals(fieldName)) {
            try {
                BigDecimal p = new BigDecimal(text.replaceAll("[^0-9.,-]", "").replace(',', '.'));
                if (p.compareTo(BigDecimal.ZERO) < 0 || p.compareTo(BigDecimal.ONE) > 0) {
                    return "p_value fora de [0, 1]";
                }
            } catch (NumberFormatException e) {
                return "p_value invalido";
            }
        }
        return null;
    }

    private static String quoteJson(String s) {
        return s == null ? "null" : "\"" + s.replace("\\", "\\\\").replace("\"", "\\\"") + "\"";
    }

    private String write(Object o) {
        try {
            return om.writeValueAsString(o);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException(e);
        }
    }
}

