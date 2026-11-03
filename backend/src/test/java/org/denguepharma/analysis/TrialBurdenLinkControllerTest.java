package org.denguepharma.analysis;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class TrialBurdenLinkControllerTest {

    private final TrialBurdenLinkController controller = new TrialBurdenLinkController();

    @Test
    void testGetTrialBurdenLinkReturnsDataAndVerifiedSafeguards() {
        Map<String, Object> response = controller.getTrialBurdenLink(null, null);

        assertNotNull(response);
        assertEquals("C", response.get("axis"));
        assertTrue(response.containsKey("summary"));

        @SuppressWarnings("unchecked")
        Map<String, Object> summary = (Map<String, Object>) response.get("summary");
        assertEquals(6, summary.get("totalSites"));
        assertEquals(true, summary.get("safeguardVerified"));

        @SuppressWarnings("unchecked")
        List<TrialBurdenLinkController.TrialBurdenLinkDTO> data =
                (List<TrialBurdenLinkController.TrialBurdenLinkDTO>) response.get("data");
        assertEquals(6, data.size());

        // Verificação Brasil
        var bra = data.stream().filter(d -> "BRA".equals(d.countryCode())).findFirst().orElseThrow();
        assertEquals(1450000L, bra.cases());
        assertEquals("COM_DADO_CARGA", bra.burdenStatus());
        assertTrue(bra.hasBurdenData());

        // Verificação ACC-ANA-004: França sem registro de carga endêmica
        var fra = data.stream().filter(d -> "FRA".equals(d.countryCode())).findFirst().orElseThrow();
        assertNull(fra.cases(), "País sem registro de carga deve ter cases=null, nunca 0");
        assertNull(fra.incidencePer100k());
        assertEquals("SEM_DADO_CARGA", fra.burdenStatus());
        assertFalse(fra.hasBurdenData());
    }

    @Test
    void testFilterByCountryAndDisparity() {
        Map<String, Object> response = controller.getTrialBurdenLink("IND", null);
        @SuppressWarnings("unchecked")
        List<TrialBurdenLinkController.TrialBurdenLinkDTO> data =
                (List<TrialBurdenLinkController.TrialBurdenLinkDTO>) response.get("data");

        assertEquals(1, data.size());
        assertEquals("DESERTO_CRITICO", data.get(0).disparityIndicator());
    }
}
