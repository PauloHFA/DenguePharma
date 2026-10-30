package org.denguepharma.analysis;

import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;

import java.util.List;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class BioactivityControllerTest {

    @Test
    void listBioactivitiesReturnsMappedDTOs() {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        BioactivityController.BioactivityDTO mockDto = new BioactivityController.BioactivityDTO(
                UUID.randomUUID(),
                "Balapiravir",
                "CHEMBL_ASSAY_1",
                "NS5 RdRp",
                "Dengue virus",
                "IC50",
                1400.0,
                "nM",
                "="
        );

        when(jdbc.query(anyString(), any(RowMapper.class), any(Object[].class)))
                .thenReturn(List.of(mockDto));

        BioactivityController controller = new BioactivityController(jdbc);
        List<BioactivityController.BioactivityDTO> result = controller.listBioactivities("NS5", "Balapiravir");

        assertThat(result).hasSize(1);
        assertThat(result.get(0).substanceName()).isEqualTo("Balapiravir");
        assertThat(result.get(0).targetName()).isEqualTo("NS5 RdRp");
        assertThat(result.get(0).activityValue()).isEqualTo(1400.0);
    }
}
