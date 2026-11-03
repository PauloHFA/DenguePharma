package org.denguepharma.analysis;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class ExtractionBenchmarkControllerTest {

    @Test
    void getExtractionBenchmarkReturnsOverallMetricsAndFields() {
        ExtractionBenchmarkController controller = new ExtractionBenchmarkController();

        Map<String, Object> result = controller.getExtractionBenchmark(null);
        assertThat(result).containsKey("overall");
        assertThat(result).containsKey("strata");
        assertThat(result).containsKey("fields");

        @SuppressWarnings("unchecked")
        Map<String, Object> overall = (Map<String, Object>) result.get("overall");
        assertThat(overall.get("f1Score")).isEqualTo(0.878);
        assertThat(overall.get("precision")).isEqualTo(0.892);
        assertThat(overall.get("recall")).isEqualTo(0.865);
        assertThat(overall).containsKey("bootstrapCi95");

        @SuppressWarnings("unchecked")
        List<ExtractionBenchmarkController.FieldMetricDTO> fields =
                (List<ExtractionBenchmarkController.FieldMetricDTO>) result.get("fields");
        assertThat(fields).hasSize(7);
    }

    @Test
    void getExtractionBenchmarkFiltersByField() {
        ExtractionBenchmarkController controller = new ExtractionBenchmarkController();

        Map<String, Object> result = controller.getExtractionBenchmark("intervention");
        @SuppressWarnings("unchecked")
        List<ExtractionBenchmarkController.FieldMetricDTO> fields =
                (List<ExtractionBenchmarkController.FieldMetricDTO>) result.get("fields");
        assertThat(fields).hasSize(1);
        assertThat(fields.get(0).field()).isEqualTo("intervention");
    }
}
