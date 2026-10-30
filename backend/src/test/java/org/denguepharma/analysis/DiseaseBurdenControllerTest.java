package org.denguepharma.analysis;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class DiseaseBurdenControllerTest {

    @Test
    void getDiseaseBurdenReturnsAllAndFiltersDeserts() {
        DiseaseBurdenController controller = new DiseaseBurdenController();

        Map<String, Object> all = controller.getDiseaseBurden(null, false);
        assertThat(all).containsKey("data");
        List<?> list = (List<?>) all.get("data");
        assertThat(list).hasSize(7);

        Map<String, Object> deserts = controller.getDiseaseBurden(null, true);
        List<?> desertList = (List<?>) deserts.get("data");
        assertThat(desertList).hasSize(3); // Bangladesh, Indonesia, India
    }
}
