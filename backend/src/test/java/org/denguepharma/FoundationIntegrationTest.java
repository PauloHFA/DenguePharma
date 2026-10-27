package org.denguepharma;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.EnumSet;
import java.util.UUID;
import org.denguepharma.user.AppUser;
import org.denguepharma.user.Role;
import org.denguepharma.user.UserRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.dao.DataAccessException;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

@SpringBootTest
@AutoConfigureMockMvc
@Testcontainers
class FoundationIntegrationTest {

    @Container
    static final PostgreSQLContainer<?> PG = new PostgreSQLContainer<>("postgres:16-alpine");

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url", PG::getJdbcUrl);
        r.add("spring.datasource.username", PG::getUsername);
        r.add("spring.datasource.password", PG::getPassword);
        r.add("denguepharma.security.jwt-secret", () -> "test-secret-with-more-than-32-characters!!");
    }

    @Autowired MockMvc mvc;
    @Autowired UserRepository users;
    @Autowired PasswordEncoder encoder;
    @Autowired JdbcTemplate jdbc;
    @Autowired ObjectMapper json;

    private static final String PASSWORD = "senha-de-teste-123";

    @BeforeEach
    void seed() {
        seedUser("admin@test.org", Role.ADMINISTRADOR);
        seedUser("revisor@test.org", Role.REVISOR);
    }

    private void seedUser(String email, Role role) {
        if (users.findByEmailIgnoreCase(email).isEmpty()) {
            users.save(new AppUser(email, encoder.encode(PASSWORD), email, EnumSet.of(role)));
        }
    }

    private String login(String email, String password) throws Exception {
        String body = json.writeValueAsString(java.util.Map.of("email", email, "password", password));
        String res = mvc.perform(post("/api/auth/login").contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString();
        JsonNode node = json.readTree(res);
        return node.get("token").asText();
    }

    // ---- RNF-01: autenticação e acesso cruzado ----

    @Test
    void loginComSenhaErradaRetorna401() throws Exception {
        String body = json.writeValueAsString(java.util.Map.of("email", "admin@test.org", "password", "errada"));
        mvc.perform(post("/api/auth/login").contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void semTokenRetorna401() throws Exception {
        mvc.perform(get("/api/auth/me")).andExpect(status().isUnauthorized());
        mvc.perform(get("/api/admin/users")).andExpect(status().isUnauthorized());
    }

    @Test
    void revisorNaoAcessaAdministracao() throws Exception {
        String token = login("revisor@test.org", PASSWORD);
        mvc.perform(get("/api/admin/users").header("Authorization", "Bearer " + token))
                .andExpect(status().isForbidden());
    }

    @Test
    void administradorListaUsuariosEMeRetornaPapeis() throws Exception {
        String token = login("admin@test.org", PASSWORD);
        mvc.perform(get("/api/admin/users").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk());
        mvc.perform(get("/api/auth/me").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.roles[0]").value("ADMINISTRADOR"));
    }

    @Test
    void loginFicaRegistradoNaAuditoria() throws Exception {
        login("admin@test.org", PASSWORD);
        Integer n = jdbc.queryForObject("select count(*) from audit_log where action = 'LOGIN'", Integer.class);
        assertThat(n).isGreaterThan(0);
    }

    // ---- Integridade do banco (seção 12) ----

    @Test
    void auditLogEAppendOnly() {
        jdbc.update("insert into audit_log (action, entity_type) values ('X','teste')");
        assertThatThrownBy(() -> jdbc.update("update audit_log set action = 'Y'"))
                .isInstanceOf(DataAccessException.class);
        assertThatThrownBy(() -> jdbc.update("delete from audit_log"))
                .isInstanceOf(DataAccessException.class);
    }

    @Test
    void identificadorExternoEUnicoPorFonteETipo() {
        UUID s1 = UUID.randomUUID();
        UUID s2 = UUID.randomUUID();
        jdbc.update("insert into study (id) values (?)", s1);
        jdbc.update("insert into study (id) values (?)", s2);
        jdbc.update("insert into study_identifier (study_id, source, id_type, value) values (?, 'CT', 'NCT', 'NCT01')", s1);
        assertThatThrownBy(() -> jdbc.update(
                "insert into study_identifier (study_id, source, id_type, value) values (?, 'CT', 'NCT', 'NCT01')", s2))
                .isInstanceOf(DataAccessException.class);
    }

    @Test
    void campoPresenteExigeTrechoDeSuporte() {
        UUID run = extractionRun("hash-a");
        assertThatThrownBy(() -> jdbc.update(
                "insert into extracted_field (extraction_run_id, field_name, original_value, absence_status) "
                        + "values (?, 'sample_size', '10', 'PRESENTE')", run))
                .isInstanceOf(DataAccessException.class);
        // Abstenção explícita é permitida sem trecho.
        jdbc.update("insert into extracted_field (extraction_run_id, field_name, absence_status) "
                + "values (?, 'sample_size', 'INCERTO')", run);
    }

    @Test
    void campoAprovadoNaoESobrescrito() {
        UUID run = extractionRun("hash-b");
        UUID field = UUID.randomUUID();
        jdbc.update("insert into extracted_field (id, extraction_run_id, field_name, absence_status, review_status) "
                + "values (?, ?, 'design', 'NAO_INFORMADO', 'APROVADO')", field, run);
        assertThatThrownBy(() -> jdbc.update(
                "update extracted_field set absence_status = 'INCERTO' where id = ?", field))
                .isInstanceOf(DataAccessException.class);
    }

    @Test
    void naoPublicaSemAprovacao() {
        UUID run = extractionRun("hash-c");
        assertThatThrownBy(() -> jdbc.update(
                "insert into extracted_field (extraction_run_id, field_name, absence_status, published) "
                        + "values (?, 'design', 'NAO_INFORMADO', true)", run))
                .isInstanceOf(DataAccessException.class);
    }

    @Test
    void extracaoEIdempotentePelaChave() {
        UUID dv = documentVersion("hash-d");
        String sql = "insert into extraction_run (document_version_id, pipeline_version, model_provider, "
                + "model_version, prompt_hash, schema_version) values (?, 'p1', 'x', 'm1', 'ph', 's1')";
        jdbc.update(sql, dv);
        assertThatThrownBy(() -> jdbc.update(sql, dv)).isInstanceOf(DataAccessException.class);
        // Outro modelo gera nova execução lógica (reprocessamento intencional).
        jdbc.update("insert into extraction_run (document_version_id, pipeline_version, model_provider, "
                + "model_version, prompt_hash, schema_version) values (?, 'p1', 'x', 'm2', 'ph', 's1')", dv);
    }

    @Test
    void versaoDeDocumentoEImutavel() {
        UUID dv = documentVersion("hash-e");
        assertThatThrownBy(() -> jdbc.update("update document_version set license = 'x' where id = ?", dv))
                .isInstanceOf(DataAccessException.class);
    }

    @Test
    void resultadoExigeProveniencia() {
        UUID study = UUID.randomUUID();
        jdbc.update("insert into study (id) values (?)", study);
        UUID outcome = UUID.randomUUID();
        jdbc.update("insert into outcome (id, study_id, definition, category, tier) "
                + "values (?, ?, 'd', 'CLINICO', 'PRIMARIO')", outcome, study);
        assertThatThrownBy(() -> jdbc.update("insert into result (outcome_id) values (?)", outcome))
                .isInstanceOf(DataAccessException.class);
    }

    private UUID documentVersion(String hash) {
        UUID doc = UUID.randomUUID();
        UUID dv = UUID.randomUUID();
        jdbc.update("insert into document (id, doc_type) values (?, 'PUBLICACAO')", doc);
        jdbc.update("insert into document_version (id, document_id, version_no, content_hash, origin, retrieved_at) "
                + "values (?, ?, 1, ?, 'pubmed', now())", dv, doc, hash);
        return dv;
    }

    private UUID extractionRun(String hash) {
        UUID dv = documentVersion(hash);
        UUID run = UUID.randomUUID();
        jdbc.update("insert into extraction_run (id, document_version_id, pipeline_version, model_provider, "
                + "model_version, prompt_hash, schema_version) values (?, ?, 'p1', 'x', 'm1', 'ph', 's1')", run, dv);
        return run;
    }
}

