package org.denguepharma;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.net.http.HttpClient;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.denguepharma.audit.AuditService;
import org.denguepharma.ingest.HttpSupport;
import org.denguepharma.substance.PubChemClient;
import org.denguepharma.substance.StudyLinkService;
import org.denguepharma.substance.SubstanceService;
import org.denguepharma.user.Role;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;

/** Testes de integração para RF-03 (Substâncias, PubChem, Fusão e Reversão T3) e RF-04 (Triagem + PRISMA-ScR). */
class SubstanceAndScreeningIntegrationTest extends AbstractIntegrationTest {

    @Autowired AuditService audit;
    @Autowired StudyLinkService studyLinks;

    @Test
    void normalizaSubstanciaNoPubChemESeparaCombinacaoDeMonoterapia() throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/rest/pug/compound/name/celgosivir/property/Title,IUPACName/JSON", ex -> {
            byte[] b = """
                    {"PropertyTable":{"Properties":[{"CID":60734,"Title":"Celgosivir","IUPACName":"[(2R,3R,4R,5S)-butyryl]"}]}}
                    """.getBytes(StandardCharsets.UTF_8);
            ex.sendResponseHeaders(200, b.length);
            ex.getResponseBody().write(b);
            ex.close();
        });
        server.createContext("/rest/pug/compound/cid/60734/synonyms/JSON", ex -> {
            byte[] b = """
                    {"InformationList":{"Information":[{"CID":60734,"Synonym":["Celgosivir","MBI-3253","6-O-butanoylcastanospermine"]}]}}
                    """.getBytes(StandardCharsets.UTF_8);
            ex.sendResponseHeaders(200, b.length);
            ex.getResponseBody().write(b);
            ex.close();
        });
        server.start();
        try {
            String baseUrl = "http://127.0.0.1:" + server.getAddress().getPort() + "/rest/pug";
            PubChemClient client = new PubChemClient(baseUrl,
                    new HttpSupport(HttpClient.newHttpClient(), "test", 0, 2, 10, ms -> {}), json);
            SubstanceService localService = new SubstanceService(jdbc, audit, client);

            var created = localService.create(
                    new SubstanceService.SubstanceInput("celgosivir", "SMALL_MOLECULE", false, List.of()), null);
            var normalized = localService.normalizeWithPubChem(created.id(), null);

            assertThat(normalized.normalizedName()).isEqualTo("Celgosivir");
            assertThat(normalized.aliases()).anySatisfy(a -> {
                assertThat(a.get("external_source")).isEqualTo("PUBCHEM_CID");
                assertThat(a.get("external_id")).isEqualTo("60734");
            });

            var second = localService.create(
                    new SubstanceService.SubstanceInput("ribavirin", "SMALL_MOLECULE", false, List.of()), null);

            // Combinação exige ao menos 2 componentes e não pode ser normalizada como monoterapia (Seção 12).
            String token = tokenFor(Role.PESQUISADOR);
            mvc.perform(post("/api/substances").header("Authorization", token)
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(json.writeValueAsString(Map.of(
                                    "publishedName", "Combinação Incompleta",
                                    "combination", true,
                                    "componentIds", List.of(created.id())))))
                    .andExpect(status().isUnprocessableEntity());

            String comboRes = mvc.perform(post("/api/substances").header("Authorization", token)
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(json.writeValueAsString(Map.of(
                                    "publishedName", "Celgosivir + Ribavirin",
                                    "productType", "COMBINATION",
                                    "combination", true,
                                    "componentIds", List.of(created.id(), second.id())))))
                    .andExpect(status().isCreated())
                    .andExpect(jsonPath("$.combination").value(true))
                    .andReturn().getResponse().getContentAsString();
            UUID comboId = UUID.fromString(json.readTree(comboRes).get("id").asText());

            mvc.perform(post("/api/substances/" + comboId + "/normalize").header("Authorization", token))
                    .andExpect(status().isConflict());
        } finally {
            server.stop(0);
        }
    }

    @Test
    void T3_fusaoAmbiguaExigeRevisaoEPodeSerDesfeitaRestaurandoEstadoOriginal() throws Exception {
        UUID s1 = seedStudyWithDoc("Estudo Principal NCT001", "CLINICALTRIALS", "NCT", "NCT001", "TEXTO_COMPLETO");
        UUID s2 = seedStudyWithDoc("Publicacao Associada PMID999", "PUBMED", "PMID", "999", "SOMENTE_RESUMO");

        String revToken = tokenFor(Role.REVISOR);
        String adjToken = tokenFor(Role.ADJUDICADOR);

        String propRes = mvc.perform(post("/api/study-links/proposals").header("Authorization", revToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json.writeValueAsString(Map.of(
                                "primaryStudyId", s1,
                                "candidateStudyId", s2,
                                "sharedIdentifier", "10.1000/dengue.1",
                                "idType", "DOI",
                                "reason", "Mesmo ensaio reportado no registro e artigo"))))
                .andExpect(status().isCreated())
                .andReturn().getResponse().getContentAsString();
        String proposalId = json.readTree(propRes).get("id").asText();

        // Revisor não pode aprovar fusão sozinho; exige ADJUDICADOR/PESQUISADOR/ADMINISTRADOR.
        mvc.perform(post("/api/study-links/proposals/" + proposalId + "/approve").header("Authorization", revToken))
                .andExpect(status().isForbidden());

        // Adjudicador aprova a fusão.
        mvc.perform(post("/api/study-links/proposals/" + proposalId + "/approve").header("Authorization", adjToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"reportRole\":\"PUBLICACAO_PRINCIPAL\"}"))
                .andExpect(status().isOk());

        assertThat(jdbc.queryForObject("select merged_into_id from study where id = ?", UUID.class, s2)).isEqualTo(s1);
        assertThat(jdbc.queryForObject("select count(*) from study_document where study_id = ?", Integer.class, s1)).isEqualTo(2);
        assertThat(jdbc.queryForObject("select count(*) from study_identifier where study_id = ?", Integer.class, s1)).isEqualTo(2);

        // Desfaz a fusão (RF-03) e confere restauração exata.
        mvc.perform(post("/api/study-links/proposals/" + proposalId + "/undo").header("Authorization", adjToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"reason\":\"Ensaios distintos da mesma coorte\"}"))
                .andExpect(status().isOk());

        assertThat(jdbc.queryForObject("select merged_into_id from study where id = ?", UUID.class, s2)).isNull();
        assertThat(jdbc.queryForObject("select screening_status from study where id = ?", String.class, s2))
                .isEqualTo("AGUARDANDO_TITULO_RESUMO");
        assertThat(jdbc.queryForObject("select count(*) from study_document where study_id = ?", Integer.class, s1)).isEqualTo(1);
        assertThat(jdbc.queryForObject("select count(*) from study_identifier where study_id = ?", Integer.class, s2)).isEqualTo(1);
    }

    @Test
    void triagemIndependenteDuplaAdjudicacaoEFluxogramaPrisma() throws Exception {
        UUID sClinical = seedStudyWithDoc("Ensaio Celgosivir Humano", "PUBMED", "PMID", "101", "TEXTO_COMPLETO");
        UUID sPreClinical = seedStudyWithDoc("Celgosivir In Vitro Vero", "PUBMED", "PMID", "102", "SOMENTE_RESUMO");
        UUID sVaccine = seedStudyWithDoc("Vacina Tetravalente Dengue", "PUBMED", "PMID", "103", "SOMENTE_RESUMO");

        String rev1 = tokenForEmail("revisor@test.org");
        String rev2 = tokenForEmail("revisor2@test.org");
        String adj = tokenFor(Role.ADJUDICADOR);

        // 1) sClinical: Revisor 1 inclui em título/resumo. Revisor 2 não enxerga o voto do Revisor 1 na fila cega!
        mvc.perform(post("/api/screening/decisions").header("Authorization", rev1)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json.writeValueAsString(Map.of(
                                "studyId", sClinical, "stage", "TITULO_RESUMO", "decision", "INCLUIR"))))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.screeningStatus").value("AGUARDANDO_TITULO_RESUMO"));

        String queueForRev2 = mvc.perform(get("/api/screening/studies").header("Authorization", rev2))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString();
        JsonNode studiesNode = json.readTree(queueForRev2);
        for (JsonNode st : studiesNode) {
            if (sClinical.toString().equals(st.get("id").asText())) {
                assertThat(st.get("decisions")).isEmpty(); // cegamento confirmado
            }
        }

        // Revisor 2 discorda em sClinical -> gera DIVERGENCIA_TITULO_RESUMO
        mvc.perform(post("/api/screening/decisions").header("Authorization", rev2)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json.writeValueAsString(Map.of(
                                "studyId", sClinical, "stage", "TITULO_RESUMO", "decision", "EXCLUIR"))))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.screeningStatus").value("DIVERGENCIA_TITULO_RESUMO"));

        // Adjudicador resolve a divergência incluindo para texto completo
        mvc.perform(post("/api/screening/decisions").header("Authorization", adj)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json.writeValueAsString(Map.of(
                                "studyId", sClinical, "stage", "TITULO_RESUMO",
                                "decision", "INCLUIR", "adjudication", true))))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.screeningStatus").value("AGUARDANDO_TEXTO_COMPLETO"));

        // Em TEXTO_COMPLETO, os dois revisores concordam em INCLUIR como HUMANO / TRATAMENTO -> INCLUIDO_NUCLEO
        for (String token : List.of(rev1, rev2)) {
            mvc.perform(post("/api/screening/decisions").header("Authorization", token)
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(json.writeValueAsString(Map.of(
                                    "studyId", sClinical, "stage", "TEXTO_COMPLETO",
                                    "decision", "INCLUIR", "context", "HUMANO", "purpose", "TRATAMENTO"))))
                    .andExpect(status().isCreated());
        }
        assertThat(jdbc.queryForObject("select screening_status from study where id = ?", String.class, sClinical))
                .isEqualTo("INCLUIDO_NUCLEO");

        // 2) sPreClinical: encaminhado para CAMADA_COMPLEMENTAR (fora da contagem clínica primária, RC-01)
        mvc.perform(post("/api/screening/decisions").header("Authorization", adj)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json.writeValueAsString(Map.of(
                                "studyId", sPreClinical, "stage", "TEXTO_COMPLETO",
                                "decision", "EXCLUIR", "exclusionCategory", "PRE_CLINICO",
                                "exclusionReason", "Ensaio celular em linhagem Vero",
                                "context", "IN_VITRO", "adjudication", true))))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.screeningStatus").value("CAMADA_COMPLEMENTAR"));

        // 3) sVaccine: excluído em título/resumo pelos dois revisores
        for (String token : List.of(rev1, rev2)) {
            mvc.perform(post("/api/screening/decisions").header("Authorization", token)
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(json.writeValueAsString(Map.of(
                                    "studyId", sVaccine, "stage", "TITULO_RESUMO",
                                    "decision", "EXCLUIR", "exclusionCategory", "VACINA",
                                    "exclusionReason", "Imunizacao preventiva"))))
                    .andExpect(status().isCreated());
        }

        // Confere fluxograma PRISMA-ScR e preservação de todas as decisões individuais (RF-04)
        mvc.perform(get("/api/screening/flowchart").header("Authorization", tokenFor(Role.LEITOR)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.identified").value(3))
                .andExpect(jsonPath("$.screened").value(3))
                .andExpect(jsonPath("$.excludedTitleAbstract").value(1))
                .andExpect(jsonPath("$.complementaryPreClinical").value(1))
                .andExpect(jsonPath("$.includedCoreClinical").value(1));

        Integer preservedDecisions = jdbc.queryForObject(
                "select count(*) from screening_decision where study_id = ?", Integer.class, sClinical);
        assertThat(preservedDecisions).isEqualTo(5); // 2 em título/resumo + 1 adjudicação + 2 em texto completo
    }

    private UUID seedStudyWithDoc(String title, String source, String idType, String extId, String accessStatus) {
        UUID studyId = jdbc.queryForObject("insert into study (title) values (?) returning id", UUID.class, title);
        jdbc.update("insert into study_identifier (study_id, source, id_type, value) values (?, ?, ?, ?)",
                studyId, source, idType, extId);
        UUID docId = jdbc.queryForObject("insert into document (doc_type, title) values ('PUBLICACAO', ?) returning id",
                UUID.class, title);
        jdbc.update("""
                insert into document_version (document_id, version_no, content_hash, origin, access_status, retrieved_at, metadata)
                values (?, 1, ?, ?, ?, now(), '{"abstract":"Resumo de teste"}'::jsonb)
                """, docId, "hash-" + extId, source, accessStatus);
        jdbc.update("""
                insert into study_document (study_id, document_id, report_role, link_certainty)
                values (?, ?, 'PUBLICACAO_PRINCIPAL', 'CONFIRMADO')
                """, studyId, docId);
        return studyId;
    }
}

