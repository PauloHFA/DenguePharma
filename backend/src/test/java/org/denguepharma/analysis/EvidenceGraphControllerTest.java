package org.denguepharma.analysis;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;

import java.util.List;
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
        assertThat(graph.metadata()).containsKey("safeguard");
    }

    @Test
    @DisplayName("REQ-ANA-008: Campos em rascunho NÃO geram arestas; apenas registros aprovados geram topologia")
    void testDraftFieldsDoNotGenerateGraphEdges() {
        List<EvidenceGraphController.ClinicalEvidenceRecord> mixed = List.of(
                new EvidenceGraphController.ClinicalEvidenceRecord("NCT01", "Ivermectina", "Clareamento Viral", "Placebo", "RASCUNHO_IA"),
                new EvidenceGraphController.ClinicalEvidenceRecord("NCT02", "Cloroquina", "Duração da Febre", "Controle", "EM_REVISAO"),
                new EvidenceGraphController.ClinicalEvidenceRecord("NCT03", "Celgosivir", "Redução Carga Viral", "Placebo", "APROVADO"),
                new EvidenceGraphController.ClinicalEvidenceRecord("NCT04", "Balapiravir", "Mortalidade", "Placebo", "REJEITADO")
        );

        EvidenceGraphController.EvidenceGraphResponse graph = EvidenceGraphController.buildNetworkFromEvidence(mixed);

        assertThat(graph.edges()).hasSize(3); // substância->estudo, estudo->desfecho, estudo->comparador
        assertThat(graph.metadata()).containsEntry("draftsIgnored", 3);
        assertThat(graph.metadata()).containsEntry("safeguardVerified", true);

        // Arestas pertencem unicamente ao estudo aprovado (Celgosivir)
        assertThat(graph.edges()).allMatch(e -> "APROVADO".equals(e.evidenceLevel()));
        assertThat(graph.edges()).noneMatch(e -> e.source().contains("ivermectina") || e.target().contains("ivermectina"));
        assertThat(graph.edges()).noneMatch(e -> e.source().contains("cloroquina") || e.target().contains("cloroquina"));
        assertThat(graph.edges()).noneMatch(e -> e.source().contains("balapiravir") || e.target().contains("balapiravir"));
    }
}
