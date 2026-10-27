package org.denguepharma;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.denguepharma.user.Role;
import org.junit.jupiter.api.Test;
import org.springframework.dao.DataAccessException;
import org.springframework.http.MediaType;

class ProtocolIntegrationTest extends AbstractIntegrationTest {

    private Map<String, Object> body(String code) {
        return Map.of(
                "code", code,
                "title", "Revisao de escopo - intervencoes farmacologicas para dengue",
                "question", "Quais intervencoes farmacologicas foram estudadas em humanos com dengue?",
                "sources", List.of("PUBMED", "CLINICALTRIALS"),
                "strategy", Map.of(
                        "pubmed", Map.of("query", "(\"Dengue\"[Mesh] OR dengue[tiab]) AND (antiviral*[tiab])"),
                        "clinicaltrials", Map.of("condition", "dengue")),
                "eligibility", Map.of("include", "estudo primario em humanos ou registro de ensaio"),
                "cutoffDate", "2026-10-26");
    }

    private JsonNode create(String token, String code) throws Exception {
        String res = mvc.perform(post("/api/protocols").header("Authorization", token)
                        .contentType(MediaType.APPLICATION_JSON).content(json.writeValueAsString(body(code))))
                .andExpect(status().isCreated()).andExpect(jsonPath("$.status").value("DRAFT"))
                .andExpect(jsonPath("$.version").value(1)).andReturn().getResponse().getContentAsString();
        return json.readTree(res);
    }

    @Test
    void leitorNaoAcessaProtocolos() throws Exception {
        mvc.perform(get("/api/protocols").header("Authorization", tokenFor(Role.LEITOR)))
                .andExpect(status().isForbidden());
    }

    @Test
    void registrarTornaProtocoloImutavel() throws Exception {
        String token = tokenFor(Role.PESQUISADOR);
        String id = create(token, "DENGUE-ESCOPO").get("id").asText();

        mvc.perform(post("/api/protocols/" + id + "/register").header("Authorization", token))
                .andExpect(status().isOk()).andExpect(jsonPath("$.status").value("REGISTERED"));

        // API recusa edição de versão registrada
        mvc.perform(put("/api/protocols/" + id).header("Authorization", token)
                        .contentType(MediaType.APPLICATION_JSON).content(json.writeValueAsString(body("DENGUE-ESCOPO"))))
                .andExpect(status().isConflict());

        // Banco recusa mesmo se a API for contornada
        assertThatThrownBy(() -> jdbc.update("update protocol set title = 'outro' where id = ?::uuid", id))
                .isInstanceOf(DataAccessException.class);
        assertThatThrownBy(() -> jdbc.update("delete from protocol where id = ?::uuid", id))
                .isInstanceOf(DataAccessException.class);
    }

    @Test
    void novaVersaoPreservaAAnterior() throws Exception {
        String token = tokenFor(Role.PESQUISADOR);
        String id = create(token, "DENGUE-ESCOPO").get("id").asText();
        mvc.perform(post("/api/protocols/" + id + "/register").header("Authorization", token)).andExpect(status().isOk());

        mvc.perform(post("/api/protocols/" + id + "/new-version").header("Authorization", token)
                        .contentType(MediaType.APPLICATION_JSON).content("{\"reason\":\"ajuste de sinonimos\"}"))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.version").value(2)).andExpect(jsonPath("$.status").value("DRAFT"));

        Integer versions = jdbc.queryForObject("select count(*) from protocol where code = 'DENGUE-ESCOPO'", Integer.class);
        assertThat(versions).isEqualTo(2);
        assertThat(jdbc.queryForObject("select status from protocol where code = 'DENGUE-ESCOPO' and version = 1", String.class))
                .isEqualTo("REGISTERED");
    }

    @Test
    void registroExigeEstrategiaParaCadaFonte() throws Exception {
        String token = tokenFor(Role.PESQUISADOR);
        Map<String, Object> incomplete = new java.util.HashMap<>(body("SEM-ESTRATEGIA"));
        incomplete.put("strategy", Map.of("pubmed", Map.of("query", "dengue")));
        String res = mvc.perform(post("/api/protocols").header("Authorization", token)
                        .contentType(MediaType.APPLICATION_JSON).content(json.writeValueAsString(incomplete)))
                .andExpect(status().isCreated()).andReturn().getResponse().getContentAsString();
        String id = json.readTree(res).get("id").asText();

        mvc.perform(post("/api/protocols/" + id + "/register").header("Authorization", token))
                .andExpect(status().isUnprocessableEntity());
    }

    @Test
    void execucaoExigeProtocoloRegistrado() throws Exception {
        String token = tokenFor(Role.PESQUISADOR);
        UUID id = UUID.fromString(create(token, "RASCUNHO").get("id").asText());
        // Backstop no banco: search_run só aceita protocolo registrado
        assertThatThrownBy(() -> jdbc.update(
                "insert into search_run (protocol_id, source, query, connector_version) values (?, 'PUBMED', 'q', 'v')", id))
                .isInstanceOf(DataAccessException.class);
    }

    @Test
    void codigoDuplicadoRetorna409() throws Exception {
        String token = tokenFor(Role.PESQUISADOR);
        create(token, "DUP");
        mvc.perform(post("/api/protocols").header("Authorization", token)
                        .contentType(MediaType.APPLICATION_JSON).content(json.writeValueAsString(body("DUP"))))
                .andExpect(status().isConflict());
    }
}

