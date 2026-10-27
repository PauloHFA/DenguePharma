package org.denguepharma.screening;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.denguepharma.audit.AuditService;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

/**
 * RF-04 e Seção 07: Triagem independente por dois revisores e adjudicação,
 * preservando todas as decisões individuais (append-only) e contabilizando o fluxograma PRISMA-ScR.
 */
@Service
public class ScreeningService {

    public static final Set<String> STAGES = Set.of("TITULO_RESUMO", "TEXTO_COMPLETO");
    public static final Set<String> DECISIONS = Set.of("INCLUIR", "EXCLUIR", "INCERTO");
    public static final Set<String> CONTEXTS = Set.of(
            "NAO_CLASSIFICADO", "HUMANO", "DESAFIO_CONTROLADO", "IN_SILICO", "IN_VITRO", "ANIMAL");
    public static final Set<String> PURPOSES = Set.of(
            "PROFILAXIA", "TRATAMENTO", "MANEJO_SINTOMATICO", "OUTRO");
    public static final Set<String> EXCLUSION_CATEGORIES = Set.of(
            "REVISAO_EDITORIAL_NOTICIA", "VACINA", "CONTROLE_VETOR",
            "DIAGNOSTICO_ISOLADO", "DOENCA_DISTINTA", "PRE_CLINICO", "DUPLICADO", "OUTRO");

    public record DecisionInput(UUID studyId, String stage, String decision, String exclusionCategory,
                                String exclusionReason, String context, String purpose,
                                boolean withoutPostedResults, boolean adjudication) {}

    private final JdbcTemplate jdbc;
    private final AuditService audit;

    public ScreeningService(JdbcTemplate jdbc, AuditService audit) {
        this.jdbc = jdbc;
        this.audit = audit;
    }

    /**
     * Lista estudos para triagem. Para preservar avaliação independente (Seção 07),
     * decisões de outros revisores na etapa aberta são ocultadas até que 2 revisores tenham votado.
     */
    public List<Map<String, Object>> queue(UUID viewerId, boolean isAdjudicator) {
        List<Map<String, Object>> studies = jdbc.queryForList("""
                select s.id, s.title, s.context, s.purpose, s.screening_status,
                       s.exclusion_category, s.final_exclusion_reason, s.created_at,
                       (select jsonb_agg(jsonb_build_object('source', si.source, 'type', si.id_type, 'value', si.value))
                        from study_identifier si where si.study_id = s.id) as identifiers,
                       (select dv.access_status from document_version dv
                        join study_document sd on sd.document_id = dv.document_id
                        where sd.study_id = s.id order by dv.version_no desc limit 1) as access_status,
                       (select dv.metadata->>'abstract' from document_version dv
                        join study_document sd on sd.document_id = dv.document_id
                        where sd.study_id = s.id order by dv.version_no desc limit 1) as abstract_text
                from study s
                where s.merged_into_id is null
                order by s.created_at desc
                """);

        for (Map<String, Object> s : studies) {
            UUID studyId = (UUID) s.get("id");
            String status = (String) s.get("screening_status");
            boolean blindStage = "AGUARDANDO_TITULO_RESUMO".equals(status) || "AGUARDANDO_TEXTO_COMPLETO".equals(status);

            List<Map<String, Object>> decisions = jdbc.queryForList("""
                    select id, reviewer_id, stage, decision, exclusion_reason, is_adjudication, created_at
                    from screening_decision
                    where study_id = ?
                    order by created_at asc
                    """, studyId);

            if (blindStage && !isAdjudicator) {
                decisions = decisions.stream()
                        .filter(d -> viewerId.equals(d.get("reviewer_id")))
                        .toList();
            }
            s.put("decisions", decisions);
        }
        return studies;
    }

    @Transactional
    public Map<String, Object> recordDecision(DecisionInput in, UUID actorId, boolean hasAdjudicatorRole) {
        validateInput(in, hasAdjudicatorRole);

        List<Map<String, Object>> studyRows = jdbc.queryForList(
                "select id, screening_status, context, purpose from study where id = ? and merged_into_id is null",
                in.studyId());
        if (studyRows.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "estudo nao encontrado ou absorvido por fusao");
        }
        String currentStatus = (String) studyRows.get(0).get("screening_status");

        String formattedReason = formatReason(in.exclusionCategory(), in.exclusionReason());
        UUID decisionId = UUID.randomUUID();
        try {
            jdbc.update("""
                    insert into screening_decision (id, study_id, reviewer_id, stage, decision, exclusion_reason, is_adjudication)
                    values (?, ?, ?, ?, ?, ?, ?)
                    """, decisionId, in.studyId(), actorId, in.stage(), in.decision(), formattedReason, in.adjudication());
        } catch (DuplicateKeyException e) {
            throw new ResponseStatusException(HttpStatus.CONFLICT,
                    "revisor ja registrou decisao independente nesta etapa para este estudo");
        }

        String nextStatus = computeNextStatus(in, currentStatus);
        String nextContext = in.context() != null && !in.context().isBlank()
                ? in.context() : (String) studyRows.get(0).get("context");
        String nextPurpose = in.purpose() != null && !in.purpose().isBlank()
                ? in.purpose() : (String) studyRows.get(0).get("purpose");

        if ( isPreClinical(nextContext) && "INCLUIR".equals(in.decision()) && "TEXTO_COMPLETO".equals(in.stage())) {
            // RC-01 / Seção 07: Estudos pré-clínicos encaminhados para camada complementar, fora da contagem clínica.
            nextStatus = "CAMADA_COMPLEMENTAR";
        }

        String exclCat = ("EXCLUIR".equals(in.decision()) && ("EXCLUIDO".equals(nextStatus) || "CAMADA_COMPLEMENTAR".equals(nextStatus)))
                ? in.exclusionCategory() : null;
        String finalReason = ("EXCLUIDO".equals(nextStatus) || "CAMADA_COMPLEMENTAR".equals(nextStatus))
                ? formattedReason : null;

        jdbc.update("""
                update study set screening_status = ?, context = ?, purpose = ?,
                       exclusion_category = coalesce(?, exclusion_category),
                       final_exclusion_reason = coalesce(?, final_exclusion_reason)
                where id = ?
                """, nextStatus, nextContext, nextPurpose, exclCat, finalReason, in.studyId());

        audit.record(actorId, in.adjudication() ? "SCREENING_ADJUDICATED" : "SCREENING_DECIDED",
                "study", in.studyId().toString(),
                "{\"screening_status\":\"" + currentStatus + "\"}",
                "{\"screening_status\":\"" + nextStatus + "\",\"decision\":\"" + in.decision() + "\"}",
                formattedReason);

        return Map.of("decisionId", decisionId, "screeningStatus", nextStatus);
    }

    private String computeNextStatus(DecisionInput in, String currentStatus) {
        if (in.adjudication()) {
            if ("INCLUIR".equals(in.decision())) {
                if ("TITULO_RESUMO".equals(in.stage())) {
                    return "AGUARDANDO_TEXTO_COMPLETO";
                }
                return in.withoutPostedResults() ? "INCLUIDO_SEM_RESULTADO" : "INCLUIDO_NUCLEO";
            }
            if ("PRE_CLINICO".equals(in.exclusionCategory())) {
                return "CAMADA_COMPLEMENTAR";
            }
            return "EXCLUIDO";
        }

        // Avaliação independente: exige 2 revisores na etapa antes de consolidar ou sinalizar divergência.
        List<String> stageDecisions = jdbc.queryForList("""
                select decision from screening_decision
                where study_id = ? and stage = ? and is_adjudication = false
                order by created_at asc
                """, String.class, in.studyId(), in.stage());

        if (stageDecisions.size() < 2) {
            return currentStatus;
        }
        String d1 = stageDecisions.get(0);
        String d2 = stageDecisions.get(1);
        if (!d1.equals(d2) || "INCERTO".equals(d1)) {
            return "TITULO_RESUMO".equals(in.stage())
                    ? "DIVERGENCIA_TITULO_RESUMO" : "DIVERGENCIA_TEXTO_COMPLETO";
        }
        if ("INCLUIR".equals(d1)) {
            if ("TITULO_RESUMO".equals(in.stage())) {
                return "AGUARDANDO_TEXTO_COMPLETO";
            }
            return in.withoutPostedResults() ? "INCLUIDO_SEM_RESULTADO" : "INCLUIDO_NUCLEO";
        }
        if ("PRE_CLINICO".equals(in.exclusionCategory())) {
            return "CAMADA_COMPLEMENTAR";
        }
        return "EXCLUIDO";
    }

    /** Contabiliza o fluxograma PRISMA-ScR (Seção 07). */
    public Map<String, Object> prismaFlowchart() {
        int totalIdentified = count("select count(*) from study");
        int duplicatesMerged = count("select count(*) from study where merged_into_id is not null");
        int uniqueRecords = totalIdentified - duplicatesMerged;
        int awaitingTitleAbstract = count("select count(*) from study where merged_into_id is null and screening_status in ('AGUARDANDO_TITULO_RESUMO','DIVERGENCIA_TITULO_RESUMO')");
        int screened = uniqueRecords - awaitingTitleAbstract;
        int excludedTitleAbstract = count("""
                select count(*) from study s where s.merged_into_id is null and s.screening_status = 'EXCLUIDO'
                and not exists (select 1 from screening_decision sd where sd.study_id = s.id and sd.stage = 'TEXTO_COMPLETO')
                """);
        int soughtForRetrieval = screened - excludedTitleAbstract;
        int notRetrieved = count("""
                select count(distinct s.id) from study s
                join study_document sd on sd.study_id = s.id
                join document_version dv on dv.document_id = sd.document_id
                where s.merged_into_id is null and dv.access_status in ('TEXTO_NAO_OBTIDO','SOMENTE_RESUMO')
                  and s.screening_status in ('AGUARDANDO_TEXTO_COMPLETO','DIVERGENCIA_TEXTO_COMPLETO')
                """);
        int excludedFullText = count("""
                select count(*) from study s where s.merged_into_id is null and s.screening_status = 'EXCLUIDO'
                and exists (select 1 from screening_decision sd where sd.study_id = s.id and sd.stage = 'TEXTO_COMPLETO')
                """);
        int complementaryPreClinical = count("select count(*) from study where merged_into_id is null and screening_status = 'CAMADA_COMPLEMENTAR'");
        int includedCore = count("select count(*) from study where merged_into_id is null and screening_status = 'INCLUIDO_NUCLEO'");
        int includedOngoingNoResults = count("select count(*) from study where merged_into_id is null and screening_status = 'INCLUIDO_SEM_RESULTADO'");

        List<Map<String, Object>> exclusionBreakdown = jdbc.queryForList("""
                select coalesce(exclusion_category, 'NAO_CATEGORIZADO') as category, count(*) as total
                from study
                where merged_into_id is null and screening_status in ('EXCLUIDO','CAMADA_COMPLEMENTAR')
                group by coalesce(exclusion_category, 'NAO_CATEGORIZADO')
                order by total desc
                """);

        Map<String, Object> out = new LinkedHashMap<>();
        out.put("identified", totalIdentified);
        out.put("duplicatesRemoved", duplicatesMerged);
        out.put("uniqueRecords", uniqueRecords);
        out.put("awaitingTitleAbstract", awaitingTitleAbstract);
        out.put("screened", screened);
        out.put("excludedTitleAbstract", excludedTitleAbstract);
        out.put("soughtForRetrieval", soughtForRetrieval);
        out.put("accessLimitedOrNotRetrieved", notRetrieved);
        out.put("excludedFullText", excludedFullText);
        out.put("complementaryPreClinical", complementaryPreClinical);
        out.put("includedCoreClinical", includedCore);
        out.put("includedWithoutResults", includedOngoingNoResults);
        out.put("exclusionBreakdown", exclusionBreakdown);
        return out;
    }

    private void validateInput(DecisionInput in, boolean hasAdjudicatorRole) {
        if (!STAGES.contains(in.stage())) {
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, "etapa invalida: " + in.stage());
        }
        if (!DECISIONS.contains(in.decision())) {
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, "decisao invalida: " + in.decision());
        }
        if (in.adjudication() && !hasAdjudicatorRole) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "apenas ADJUDICADOR pode adjudicar divergencias");
        }
        if (in.adjudication() && "INCERTO".equals(in.decision())) {
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,
                    "adjudicacao deve resolver a divergencia (INCLUIR ou EXCLUIR)");
        }
        if ("EXCLUIR".equals(in.decision()) && "TEXTO_COMPLETO".equals(in.stage())) {
            if (in.exclusionCategory() == null || !EXCLUSION_CATEGORIES.contains(in.exclusionCategory())) {
                throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,
                        "exclusao em texto completo exige categoria padronizada");
            }
            if (in.exclusionReason() == null || in.exclusionReason().isBlank()) {
                throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,
                        "exclusao em texto completo exige justificativa textual");
            }
        }
        if (in.context() != null && !in.context().isBlank() && !CONTEXTS.contains(in.context())) {
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, "contexto invalido: " + in.context());
        }
        if (in.purpose() != null && !in.purpose().isBlank() && !PURPOSES.contains(in.purpose())) {
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, "finalidade invalida: " + in.purpose());
        }
    }

    private static boolean isPreClinical(String context) {
        return "IN_SILICO".equals(context) || "IN_VITRO".equals(context) || "ANIMAL".equals(context);
    }

    private static String formatReason(String category, String reason) {
        if ((category == null || category.isBlank()) && (reason == null || reason.isBlank())) return null;
        if (category == null || category.isBlank()) return reason.trim();
        if (reason == null || reason.isBlank()) return "[" + category + "]";
        return "[" + category + "] " + reason.trim();
    }

    private int count(String sql) {
        Integer n = jdbc.queryForObject(sql, Integer.class);
        return n == null ? 0 : n;
    }
}
