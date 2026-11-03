package org.denguepharma.analysis;

import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class PrismaFlowControllerTest {

    @Test
    void getPrismaFlowReturnsValidAccountingAndCategories() {
        PrismaFlowController controller = new PrismaFlowController();

        Map<String, Object> flow = controller.getPrismaFlow();
        assertThat(flow).containsKey("identification");
        assertThat(flow).containsKey("screening");
        assertThat(flow).containsKey("eligibility");
        assertThat(flow).containsKey("included");
        assertThat(flow).containsKey("accountingCheck");

        @SuppressWarnings("unchecked")
        Map<String, Object> check = (Map<String, Object>) flow.get("accountingCheck");
        assertThat(check.get("formulaVerified")).isEqualTo(true);
        assertThat(check.get("identifiedEqualsDuplicatesPlusScreened")).isEqualTo(true);
        assertThat(check.get("exclusionsSumMatches")).isEqualTo(true);

        @SuppressWarnings("unchecked")
        Map<String, Object> id = (Map<String, Object>) flow.get("identification");
        assertThat(id.get("totalIdentified")).isEqualTo(1450);
        assertThat(id.get("duplicatesRemoved")).isEqualTo(210);

        @SuppressWarnings("unchecked")
        Map<String, Object> screening = (Map<String, Object>) flow.get("screening");
        assertThat(screening.get("screenedRecords")).isEqualTo(1240);
        assertThat(screening.get("excludedRecords")).isEqualTo(1180);

        @SuppressWarnings("unchecked")
        Map<String, Object> inc = (Map<String, Object>) flow.get("included");
        assertThat(inc.get("includedStudies")).isEqualTo(20);
    }
}
