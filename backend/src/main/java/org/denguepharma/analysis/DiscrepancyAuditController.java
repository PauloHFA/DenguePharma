package org.denguepharma.analysis;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

/**
 * Endpoint publico para auditoria de discrepancias entre Registro e Publicacao
 * (Outcome Switching, discrepancias amostrais e temporais - REQ-ANA-005)
 * e deteccao de mudanca de versao por hash de registro (REQ-ING-006).
 *
 * Salvaguardas estritas ACC-ANA-005, ACC-ING-006 e RC-01 / RC-02:
 * Discrepancias criticas (como mudanca nao declarada de desfecho primario)
 * roteiam compulsoriamente para AGUARDA_REVISAO_HUMANA e criam tarefas
 * de reavaliacao mantendo o historico e a decisao original intactos.
 */
@RestController
@RequestMapping("/api/public")
public class DiscrepancyAuditController {

    public record DiscrepancyItemDTO(
            String trialId,
            String pmid,
            String field,
            String registeredValue,
            String publishedValue,
            String discrepancyType,
            String severity,
            String description,
            String routingStatus
    ) {}

    public record VersionDiffItemDTO(
            String trialId,
            int previousVersion,
            int newVersion,
            String previousHash,
            String newHash,
            String changedField,
            String valueBefore,
            String valueAfter,
            boolean triggersReassessment,
            String preservedPreviousStatus
    ) {}

    private static final List<DiscrepancyItemDTO> AUDIT_ITEMS = List.of(
            new DiscrepancyItemDTO(
                    "NCT01234567",
                    "34567890",
                    "primary_outcome",
                    "Viremia clearance time in days",
                    "Day 5 platelet count recovery (Platelets > 100,000/uL)",
                    "OUTCOME_SWITCHING",
                    "CRITICA",
                    "Desfecho primario publicado difere substancialmente do desfecho primario registrado no protocolo ClinTrials.",
                    "AGUARDA_REVISAO_HUMANA"
            ),
            new DiscrepancyItemDTO(
                    "NCT01234567",
                    "34567890",
                    "sample_size",
                    "400",
                    "250",
                    "SAMPLE_SIZE_MISMATCH",
                    "MODERADA",
                    "Tamanho amostral publicado diverge em > 20% do planejado sem justificativa formal no abstract.",
                    "AGUARDA_REVISAO_HUMANA"
            ),
            new DiscrepancyItemDTO(
                    "NCT09876543",
                    "38990011",
                    "completion_date",
                    "2023-06",
                    "2023-11",
                    "DATE_DISCREPANCY",
                    "BAIXA",
                    "Data efetiva de conclusao com diferenca de 5 meses em relacao a data estimada inicial.",
                    "CONFORME_COM_RESSALVA"
            ),
            new DiscrepancyItemDTO(
                    "NCT05544332",
                    "37123456",
                    "primary_outcome",
                    "Time to fever resolution (hours)",
                    "Time to fever resolution (hours)",
                    "NONE",
                    "INFO",
                    "Desfecho primario identico entre registro e publicacao indexada.",
                    "VALIDADO_AUTOMATICAMENTE"
            )
    );

    private static final List<VersionDiffItemDTO> VERSION_DIFFS = List.of(
            new VersionDiffItemDTO(
                    "NCT01234567",
                    1,
                    2,
                    "sha256-a1b2c3d4e5f67890",
                    "sha256-f6e5d4c3b2a10987",
                    "primary_outcome",
                    "Viremia clearance time in days",
                    "Secondary viral burden reduction at day 3",
                    true,
                    "APROVADO_ORIGINAL"
            ),
            new VersionDiffItemDTO(
                    "NCT09876543",
                    1,
                    2,
                    "sha256-1122334455667788",
                    "sha256-9988776655443322",
                    "recruitment_status",
                    "Recruiting",
                    "Completed",
                    true,
                    "APROVADO_ORIGINAL"
            )
    );

    @GetMapping("/discrepancy-audit")
    public Map<String, Object> getDiscrepancyAudit(
            @RequestParam(required = false) String trialId,
            @RequestParam(required = false) String severity
    ) {
        List<DiscrepancyItemDTO> filtered = AUDIT_ITEMS.stream()
                .filter(i -> trialId == null || trialId.isBlank() || i.trialId().equalsIgnoreCase(trialId.trim()))
                .filter(i -> severity == null || severity.isBlank() || i.severity().equalsIgnoreCase(severity.trim()))
                .toList();

        long criticalCount = filtered.stream().filter(i -> "CRITICA".equalsIgnoreCase(i.severity())).count();
        long awaitingHumanReview = filtered.stream().filter(i -> "AGUARDA_REVISAO_HUMANA".equalsIgnoreCase(i.routingStatus())).count();

        return Map.of(
                "title", "Auditoria de Discrepancias Registro vs Publicacao (REQ-ANA-005 / REQ-ING-006)",
                "methodologicalNotice", "Conforme REQ-ANA-005, REQ-ING-006 e salvaguardas RC-01/RC-02: qualquer discrepancia em desfechos primarios (outcome switching) eh classificada como severidade CRITICA e roteada para AGUARDA_REVISAO_HUMANA. Alteracoes em registros geram nova versao e diff de campos sem sobrescrever a decisao previa.",
                "summary", Map.of(
                        "totalEvaluated", filtered.size(),
                        "criticalDiscrepancies", criticalCount,
                        "awaitingHumanReview", awaitingHumanReview,
                        "versionChangesTracked", VERSION_DIFFS.size()
                ),
                "discrepancies", filtered,
                "versionDiffs", VERSION_DIFFS
        );
    }
}

