package org.denguepharma.catalog;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.denguepharma.audit.AuditService;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

/**
 * RF-07, RF-08, Regras Científicas RC-01 a RC-07 e Cenário T6:
 * Catálogo público de evidências aprovadas (filtros nunca ocultam limitações),
 * comparador contextualizado sem ranking clínico automático e retratação que invalida a síntese vigente preservando histórico.
 */
@Service
public class CatalogService {

    public record CatalogFilter(String substance, String purpose, String context,
                                String design, String serotype, String phase) {}

    private final JdbcTemplate jdbc;
    private final AuditService audit;

    public CatalogService(JdbcTemplate jdbc, AuditService audit) {
        this.jdbc = jdbc;
        this.audit = audit;
    }

    /**
     * RF-07: Consulta o catálogo vigente (apenas estudos ATIVO, não absorvidos em fusão e com evidência publicada
     * ou incluídos na síntese). Os filtros nunca ocultam limitações, alertas de segurança (RC-03) nem status regulatório (RC-02).
     */
    public List<Map<String, Object>> search(CatalogFilter f) {
        StringBuilder sql = new StringBuilder("""
                select s.id, s.title, s.design, s.phase, s.context, s.purpose, s.status,
                       s.serotype, s.countries, s.sample_size, s.comparator_label,
                       s.outcome_summary, s.outcome_category, s.outcome_time_frame, s.effect_summary,
                       s.adverse_events_status, s.limitations, s.risk_of_bias_tool, s.risk_of_bias_level,
                       s.regulatory_status, s.regulatory_authority, s.regulatory_jurisdiction,
                       s.regulatory_indication, s.regulatory_date,
                       sub.published_name as substance_published_name, sub.normalized_name as substance_normalized_name,
                       (select dv.access_status from document_version dv
                        join study_document sd on sd.document_id = dv.document_id
                        where sd.study_id = s.id order by dv.version_no desc limit 1) as access_status
                from study s
                left join substance sub on sub.id = s.primary_substance_id
                where s.status = 'ATIVO'
                  and s.merged_into_id is null
                  and (s.screening_status in ('INCLUIDO_NUCLEO','INCLUIDO_SEM_RESULTADO','CAMADA_COMPLEMENTAR')
                       or exists (select 1 from extracted_field ef where ef.study_id = s.id and ef.published = true))
                """);
        List<Object> params = new ArrayList<>();

        if (notBlank(f.substance())) {
            sql.append("""
                     and (lower(coalesce(sub.normalized_name, '')) like lower(?)
                       or lower(coalesce(sub.published_name, '')) like lower(?)
                       or exists (select 1 from substance_alias sa where sa.substance_id = s.primary_substance_id and lower(sa.alias) like lower(?)))
                    """);
            String pat = "%" + f.substance().trim() + "%";
            params.add(pat);
            params.add(pat);
            params.add(pat);
        }
        if (notBlank(f.purpose())) {
            sql.append(" and s.purpose = ?");
            params.add(f.purpose().trim());
        }
        if (notBlank(f.context())) {
            sql.append(" and s.context = ?");
            params.add(f.context().trim());
        }
        if (notBlank(f.design())) {
            sql.append(" and lower(coalesce(s.design, '')) = lower(?)");
            params.add(f.design().trim());
        }
        if (notBlank(f.serotype())) {
            sql.append(" and lower(coalesce(s.serotype, '')) like lower(?)");
            params.add("%" + f.serotype().trim() + "%");
        }
        if (notBlank(f.phase())) {
            sql.append(" and lower(coalesce(s.phase, '')) = lower(?)");
            params.add(f.phase().trim());
        }

        sql.append(" order by s.created_at desc");
        List<Map<String, Object>> rows = jdbc.queryForList(sql.toString(), params.toArray());

        for (Map<String, Object> r : rows) {
            UUID studyId = (UUID) r.get("id");
            List<Map<String, Object>> publishedFields = jdbc.queryForList("""
                    select ef.field_name, ef.original_value, ef.normalized_value, ef.absence_status,
                           es.section, es.locator, es.text as evidence_quote,
                           dv.origin as source, dv.version_no, dv.content_hash
                    from extracted_field ef
                    left join evidence_span es on es.id = ef.evidence_span_id
                    join extraction_run er on er.id = ef.extraction_run_id
                    join document_version dv on dv.id = er.document_version_id
                    where ef.study_id = ? and ef.published = true
                    order by ef.field_name
                    """, studyId);
            r.put("published_fields", publishedFields);
            r.put("scientific_notices", buildNotices(r));
        }
        return rows;
    }

    /**
     * RF-08 e RC-01, RC-03, RC-04: Compara evidências por desfecho/tempo com contexto visível,
     * apontando incompatibilidades metodológicas e proibindo ranking clínico automático.
     */
    public Map<String, Object> compare(List<UUID> studyIds) {
        if (studyIds == null || studyIds.size() < 2) {
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,
                    "selecione ao menos 2 estudos para comparar");
        }
        List<Map<String, Object>> items = new ArrayList<>();
        for (UUID id : studyIds) {
            List<Map<String, Object>> found = jdbc.queryForList("""
                    select s.id, s.title, s.status, s.context, s.purpose, s.design, s.phase,
                           s.serotype, s.sample_size, s.comparator_label,
                           s.outcome_summary, s.outcome_category, s.outcome_time_frame,
                           s.effect_summary, s.adverse_events_status, s.limitations,
                           s.risk_of_bias_tool, s.risk_of_bias_level, s.regulatory_status,
                           sub.published_name as substance_name
                    from study s
                    left join substance sub on sub.id = s.primary_substance_id
                    where s.id = ?
                    """, id);
            if (found.isEmpty()) {
                throw new ResponseStatusException(HttpStatus.NOT_FOUND, "estudo nao encontrado: " + id);
            }
            Map<String, Object> st = found.get(0);
            if ("RETRATADO".equals(st.get("status"))) {
                throw new ResponseStatusException(HttpStatus.CONFLICT,
                        "estudo " + id + " foi retratado e saiu da sintese vigente (RC-06 / T6)");
            }
            items.add(st);
        }

        List<Map<String, String>> incompatibilities = detectIncompatibilities(items);

        Map<String, Object> out = new LinkedHashMap<>();
        out.put("studies", items);
        out.put("compatibleForDirectSynthesis", incompatibilities.isEmpty());
        out.put("incompatibilities", incompatibilities);
        out.put("rankingPolicy", "RC-04: Esta plataforma nao gera ranking universal de melhor farmaco nem pontuacao automatica de eficacia.");
        return out;
    }

    /**
     * Cenário T6 e RC-06: Retratação invalida a síntese vigente (estudo sai imediatamente do catálogo e comparador)
     * e preserva integralmente o histórico documental, versões e decisões anteriores.
     */
    @Transactional
    public Map<String, Object> retractStudy(UUID studyId, String reason, UUID actor) {
        if (reason == null || reason.isBlank()) {
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,
                    "retratacao exige motivo documentado (RC-06)");
        }
        int updated = jdbc.update("""
                update study
                set status = 'RETRATADO', retraction_reason = ?, retracted_at = now()
                where id = ?
                """, reason.trim(), studyId);
        if (updated == 0) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "estudo nao encontrado");
        }
        jdbc.update("""
                insert into reassessment_task (study_id, trigger_type, notes)
                values (?, 'RETRATACAO', ?)
                """, studyId, reason.trim());
        audit.record(actor, "STUDY_RETRACTED", "study", studyId.toString(),
                "{\"status\":\"ATIVO\"}", "{\"status\":\"RETRATADO\"}", reason.trim());
        return Map.of("studyId", studyId, "status", "RETRATADO", "synthesisInvalidated", true);
    }

    private List<Map<String, String>> detectIncompatibilities(List<Map<String, Object>> items) {
        List<Map<String, String>> warnings = new ArrayList<>();

        Set<String> contexts = collectDistinct(items, "context");
        if (contexts.size() > 1) {
            warnings.add(Map.of(
                    "rule", "RC-01",
                    "code", "CONTEXTO_INCOMPATIVEL",
                    "message", "Bloqueio de sintese: nunca combinar automaticamente contextos experimentais distintos (" + String.join(" vs. ", contexts) + ")."));
        }

        Set<String> purposes = collectDistinct(items, "purpose");
        if (purposes.size() > 1) {
            warnings.add(Map.of(
                    "rule", "RC-01",
                    "code", "FINALIDADE_INCOMPATIVEL",
                    "message", "Incompatibilidade de finalidade: estudos avaliam usos distintos (" + String.join(" vs. ", purposes) + ")."));
        }

        Set<String> outcomeCats = collectDistinct(items, "outcome_category");
        if (outcomeCats.contains("VIROLOGICO") && outcomeCats.contains("CLINICO")) {
            warnings.add(Map.of(
                    "rule", "RC-03",
                    "code", "DESFECHO_SUBSTITUTO_VS_CLINICO",
                    "message", "RC-03: Reducao de carga viral (desfecho virologico) nao equivale a reducao de hospitalizacao ou mortalidade (desfecho clinico)."));
        }

        Set<String> timeFrames = collectDistinct(items, "outcome_time_frame");
        if (timeFrames.size() > 1) {
            warnings.add(Map.of(
                    "rule", "RC-04",
                    "code", "TEMPO_DE_DESFECHO_DIVERGENTE",
                    "message", "Janelas de avaliacao do desfecho divergem entre os estudos (" + String.join(" vs. ", timeFrames) + ")."));
        }

        Set<String> designs = collectDistinct(items, "design");
        if (designs.size() > 1) {
            warnings.add(Map.of(
                    "rule", "RC-04",
                    "code", "DESENHO_DIVERGENTE",
                    "message", "Desenhos metodologicos distintos (" + String.join(" vs. ", designs) + ")."));
        }
        return warnings;
    }

    private static Set<String> collectDistinct(List<Map<String, Object>> items, String key) {
        Set<String> set = new LinkedHashSet<>();
        for (Map<String, Object> m : items) {
            Object v = m.get(key);
            if (v != null && !String.valueOf(v).isBlank()) {
                set.add(String.valueOf(v));
            }
        }
        return set;
    }

    private static List<String> buildNotices(Map<String, Object> r) {
        List<String> notices = new ArrayList<>();
        String reg = (String) r.get("regulatory_status");
        if ("CANDIDATO_EM_PESQUISA".equals(reg)) {
            notices.add("RC-02: Candidato em pesquisa — resultado de estudo não equivale a aprovação regulatória para dengue.");
        }
        String ae = (String) r.get("adverse_events_status");
        if ("AUSENCIA_DE_RELATO".equals(ae) || "NAO_INFORMADO".equals(ae)) {
            notices.add("RC-03: Eventos adversos não relatados ou não informados não equivalem a ausência de evento adverso ('seguro').");
        }
        String ctx = (String) r.get("context");
        if ("IN_SILICO".equals(ctx) || "IN_VITRO".equals(ctx) || "ANIMAL".equals(ctx)) {
            notices.add("RC-01: Evidência pré-clínica (" + ctx + ") — camada complementar, não extrapolável para eficácia clínica em humanos.");
        }
        return notices;
    }

    private static boolean notBlank(String s) {
        return s != null && !s.isBlank();
    }
}
