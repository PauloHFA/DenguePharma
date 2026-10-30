package org.denguepharma.analysis;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Eixo E: Visualização em grafo de rede da topologia de evidências farmacológicas.
 * Conecta: Substâncias (Fármacos) -> Alvos Virais e do Hospedeiro -> Desfechos Clínicos -> Estudos.
 */
@RestController
@RequestMapping("/api/public/evidence-graph")
public class EvidenceGraphController {

    private final JdbcTemplate jdbc;

    public EvidenceGraphController(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public record GraphNode(String id, String label, String type, String group, String details) {}
    public record GraphEdge(String source, String target, String relation, String evidenceLevel) {}
    public record EvidenceGraphResponse(List<GraphNode> nodes, List<GraphEdge> edges, Map<String, Object> metadata) {}

    @GetMapping
    public EvidenceGraphResponse getGraph() {
        List<GraphNode> nodes = new ArrayList<>();
        List<GraphEdge> edges = new ArrayList<>();

        // 1. Alvos Moleculares Virais e Hospedeiro (Target Nodes)
        nodes.add(new GraphNode("tgt-ns5-rdrp", "NS5 (RdRp)", "TARGET", "VIRAL_NAO_ESTRUTURAL", "RNA polimerase dependente de RNA - replicação viral"));
        nodes.add(new GraphNode("tgt-ns5-mtase", "NS5 (MTase)", "TARGET", "VIRAL_NAO_ESTRUTURAL", "Metiltransferase - capeamento 5' do RNA genômico"));
        nodes.add(new GraphNode("tgt-ns3-prot", "NS3 (Protease)", "TARGET", "VIRAL_NAO_ESTRUTURAL", "Serino protease com cofator NS2B - clivagem poliproteica"));
        nodes.add(new GraphNode("tgt-ns3-hel", "NS3 (Helicase)", "TARGET", "VIRAL_NAO_ESTRUTURAL", "RNA helicase / NTPase - desenrolamento de RNA"));
        nodes.add(new GraphNode("tgt-protein-e", "Proteína de Envelope (E)", "TARGET", "VIRAL_ESTRUTURAL", "Ligação a receptores e fusão endossomal de membrana"));
        nodes.add(new GraphNode("tgt-host-importin", "Importinas KPNA/KPNB1", "TARGET", "FATOR_HOSPEDEIRO", "Importação nuclear de proteínas virais NS5"));
        nodes.add(new GraphNode("tgt-host-glucosidase", "Alfa-glicosidase RE", "TARGET", "FATOR_HOSPEDEIRO", "Enovelamento de glicoproteínas de envelope"));
        nodes.add(new GraphNode("tgt-host-dhodh", "DHODH Celular", "TARGET", "FATOR_HOSPEDEIRO", "Biossíntese de novo de pirimidinas para replicação"));

        // 2. Fármacos Candidatos (Substance Nodes)
        nodes.add(new GraphNode("sub-balapiravir", "Balapiravir", "SUBSTANCE", "ANTIVIRAL_DIRETO", "Pró-fármaco análogo de nucleosídeo"));
        nodes.add(new GraphNode("sub-sofosbuvir", "Sofosbuvir", "SUBSTANCE", "ANTIVIRAL_DIRETO", "Inibidor de RdRp reposicionado de HCV"));
        nodes.add(new GraphNode("sub-nitd008", "NITD-008", "SUBSTANCE", "ANTIVIRAL_DIRETO", "Análogo de adenosina inibidor da RdRp"));
        nodes.add(new GraphNode("sub-ivermectina", "Ivermectina", "SUBSTANCE", "MODULADOR_ALVO", "Inibidor de importina e helicase NS3"));
        nodes.add(new GraphNode("sub-cloroquina", "Cloroquina", "SUBSTANCE", "MODULADOR_FUSAO", "Alcalinização de endossomos e bloqueio de fusão"));
        nodes.add(new GraphNode("sub-celgosivir", "Celgosivir", "SUBSTANCE", "ALVO_HOSPEDEIRO", "Inibidor de alfa-glicosidase"));
        nodes.add(new GraphNode("sub-brequinar", "Brequinar", "SUBSTANCE", "ALVO_HOSPEDEIRO", "Inibidor de DHODH celular"));

        // 3. Desfechos Prioritários (Outcome Nodes)
        nodes.add(new GraphNode("out-clearance", "Redução de Carga Viral", "OUTCOME", "DESFECHO_VIROLOGICO", "Cinética de depuração viral / RNAemia"));
        nodes.add(new GraphNode("out-febre", "Duração e Pico de Febre", "OUTCOME", "DESFECHO_SINTOMATICO", "Alívio térmico em dias pós-início"));
        nodes.add(new GraphNode("out-plaquetopenia", "Contagem de Plaquetas", "OUTCOME", "DESFECHO_CLINICO", "Nadir plaquetário e trombocitopenia"));
        nodes.add(new GraphNode("out-grave", "Progressão para Dengue Grave", "OUTCOME", "DESFECHO_GRAVE", "Extravasamento plasmático, choque ou sangramento"));
        nodes.add(new GraphNode("out-seguranca", "Eventos Adversos Graves", "OUTCOME", "DESFECHO_SEGURANCA", "Sinais de toxicidade ou interrupção"));

        // 4. Arestas: Fármaco -> Alvo (Inibição / Ligação)
        edges.add(new GraphEdge("sub-balapiravir", "tgt-ns5-rdrp", "INIBE", "ENSAIO_CLINICO"));
        edges.add(new GraphEdge("sub-sofosbuvir", "tgt-ns5-rdrp", "INIBE", "IN_VITRO"));
        edges.add(new GraphEdge("sub-nitd008", "tgt-ns5-rdrp", "INIBE", "PRE_CLINICO"));
        edges.add(new GraphEdge("sub-ivermectina", "tgt-host-importin", "BLOQUEIA", "ENSAIO_CLINICO"));
        edges.add(new GraphEdge("sub-ivermectina", "tgt-ns3-hel", "INIBE", "IN_VITRO"));
        edges.add(new GraphEdge("sub-cloroquina", "tgt-protein-e", "MODULA_FUSAO", "ENSAIO_CLINICO"));
        edges.add(new GraphEdge("sub-celgosivir", "tgt-host-glucosidase", "INIBE", "ENSAIO_CLINICO"));
        edges.add(new GraphEdge("sub-brequinar", "tgt-host-dhodh", "INIBE", "PRE_CLINICO"));

        // 5. Arestas: Alvo -> Desfecho (Impacto Mecanístico)
        edges.add(new GraphEdge("tgt-ns5-rdrp", "out-clearance", "IMPACTA", "MECANISTICO"));
        edges.add(new GraphEdge("tgt-ns3-prot", "out-clearance", "IMPACTA", "MECANISTICO"));
        edges.add(new GraphEdge("tgt-protein-e", "out-grave", "IMPACTA", "MECANISTICO"));
        edges.add(new GraphEdge("tgt-host-glucosidase", "out-febre", "IMPACTA", "MECANISTICO"));
        edges.add(new GraphEdge("tgt-host-dhodh", "out-clearance", "IMPACTA", "MECANISTICO"));

        // 6. Consultar estudos clínicos aprovados no banco de dados e conectar ao grafo
        try {
            List<Map<String, Object>> studyRows = jdbc.queryForList("""
                    select s.id, s.title, s.design, s.phase,
                           sub.normalized_name as substance_name
                    from study s
                    join substance sub on sub.id = s.primary_substance_id
                    where s.status = 'ATIVO' and not s.is_demo
                    limit 15
                    """);

            for (Map<String, Object> row : studyRows) {
                String studyId = "std-" + row.get("id");
                String title = (String) row.get("title");
                String design = (String) row.get("design");
                String subName = (String) row.get("substance_name");

                nodes.add(new GraphNode(studyId, title != null ? (title.length() > 40 ? title.substring(0, 37) + "..." : title) : "Estudo",
                        "STUDY", "EVIDENCIA_DOCUMENTAL", "Desenho: " + design));

                // Liga ao fármaco se houver correspondência
                if (subName != null) {
                    for (GraphNode n : nodes) {
                        if ("SUBSTANCE".equals(n.type()) && subName.toLowerCase().contains(n.label().toLowerCase())) {
                            edges.add(new GraphEdge(studyId, n.id(), "AVALIA", "ENSAIO_CLINICO"));
                        }
                    }
                }
                edges.add(new GraphEdge(studyId, "out-clearance", "MENSURA", "CLINICO"));
                edges.add(new GraphEdge(studyId, "out-seguranca", "MENSURA", "CLINICO"));
            }
        } catch (Exception ignored) {
            // Se o banco não tiver estudos ainda, o grafo base conceitual permanece íntegro
        }

        Map<String, Object> meta = new HashMap<>();
        meta.put("axis", "E");
        meta.put("title", "Topologia em Grafo de Rede de Evidências Farmacológicas (Eixo E)");
        meta.put("notice", "Frequência e proximidade em rede não conferem eficácia clínica (Regra RC-01 e RC-04).");
        meta.put("nodeCount", nodes.size());
        meta.put("edgeCount", edges.size());

        return new EvidenceGraphResponse(nodes, edges, meta);
    }
}

