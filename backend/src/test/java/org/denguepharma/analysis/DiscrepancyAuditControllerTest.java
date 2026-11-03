package org.denguepharma.analysis;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class DiscrepancyAuditControllerTest {

    private final DiscrepancyAuditController controller = new DiscrepancyAuditController();

    @Test
    void testGetDiscrepancyAuditReturnsSummaryAndItems() {
        Map<String, Object> response = controller.getDiscrepancyAudit(null, null);

        assertNotNull(response);
        assertTrue(response.containsKey("summary"));
        assertTrue(response.containsKey("discrepancies"));
        assertTrue(response.containsKey("versionDiffs"));

        @SuppressWarnings("unchecked")
        Map<String, Object> summary = (Map<String, Object>) response.get("summary");
        assertEquals(4, summary.get("totalEvaluated"));
        assertEquals(1L, summary.get("criticalDiscrepancies"));
        assertEquals(2L, summary.get("awaitingHumanReview"));
        assertEquals(2, summary.get("versionChangesTracked"));

        @SuppressWarnings("unchecked")
        List<DiscrepancyAuditController.DiscrepancyItemDTO> items =
                (List<DiscrepancyAuditController.DiscrepancyItemDTO>) response.get("discrepancies");

        // Outcome switching deve ser severidade CRITICA e rotear para AGUARDA_REVISAO_HUMANA
        var outcomeSwitch = items.stream()
                .filter(i -> "OUTCOME_SWITCHING".equals(i.discrepancyType()))
                .findFirst()
                .orElseThrow();
        assertEquals("CRITICA", outcomeSwitch.severity());
        assertEquals("AGUARDA_REVISAO_HUMANA", outcomeSwitch.routingStatus());

        // Version diffs devem conter preservação de status prévio
        @SuppressWarnings("unchecked")
        List<DiscrepancyAuditController.VersionDiffItemDTO> diffs =
                (List<DiscrepancyAuditController.VersionDiffItemDTO>) response.get("versionDiffs");
        assertEquals(2, diffs.size());
        assertTrue(diffs.stream().allMatch(d -> "APROVADO_ORIGINAL".equals(d.preservedPreviousStatus())));
    }

    @Test
    void testFilterBySeverityAndTrialId() {
        Map<String, Object> response = controller.getDiscrepancyAudit("NCT01234567", "CRITICA");
        @SuppressWarnings("unchecked")
        List<DiscrepancyAuditController.DiscrepancyItemDTO> items =
                (List<DiscrepancyAuditController.DiscrepancyItemDTO>) response.get("discrepancies");

        assertEquals(1, items.size());
        assertEquals("primary_outcome", items.get(0).field());
        assertEquals("OUTCOME_SWITCHING", items.get(0).discrepancyType());
    }
}

