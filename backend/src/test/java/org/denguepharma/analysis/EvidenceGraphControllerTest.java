package org.denguepharma.analysis;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;

class EvidenceGraphControllerTest {

    @Test
    @DisplayName("Grafo de evidências deve conter nós de alvos, substâncias e desfechos com arestas mecanísticas")
    void getGraphContainsRequiredTopology() {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        EvidenceGraphController controller = new EvidenceGraphController(jdbc);

        EvidenceGraphController.EvidenceGraphResponse graph = controller.getGraph();

        assertThat(graph.nodes()).isNotEmpty();
        assertThat(graph.edges()).isNotEmpty();

        assertThat(graph.nodes()).anyMatch(n -> "TARGET".equals(n.type()) && n.id().equals("tgt-ns5-rdrp"));
        assertThat(graph.nodes()).anyMatch(n -> "SUBSTANCE".equals(n.type()) && n.id().equals("sub-balapiravir"));
        assertThat(graph.nodes()).anyMatch(n -> "OUTCOME".equals(n.type()) && n.id().equals("out-clearance"));

        assertThat(graph.edges()).anyMatch(e -> e.source().equals("sub-balapiravir") && e.target().equals("tgt-ns5-rdrp") && e.relation().equals("INIBE"));
        assertThat(graph.edges()).anyMatch(e -> e.source().equals("tgt-ns5-rdrp") && e.target().equals("out-clearance"));

        assertThat(graph.metadata()).containsEntry("axis", "E");
    }
}

