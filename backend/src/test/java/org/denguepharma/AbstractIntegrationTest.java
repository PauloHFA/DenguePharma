package org.denguepharma;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.EnumSet;
import java.util.Map;
import org.denguepharma.user.AppUser;
import org.denguepharma.user.Role;
import org.denguepharma.user.UserRepository;
import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.testcontainers.containers.PostgreSQLContainer;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Base com um PostgreSQL único por JVM e usuários de cada papel. */
@SpringBootTest
@AutoConfigureMockMvc
abstract class AbstractIntegrationTest {

    static final PostgreSQLContainer<?> PG = new PostgreSQLContainer<>("postgres:16-alpine");

    static {
        PG.start();
    }

    static final String PASSWORD = "senha-de-teste-123";

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url", PG::getJdbcUrl);
        r.add("spring.datasource.username", PG::getUsername);
        r.add("spring.datasource.password", PG::getPassword);
        r.add("denguepharma.security.jwt-secret", () -> "test-secret-with-more-than-32-characters!!");
    }

    @Autowired protected MockMvc mvc;
    @Autowired protected JdbcTemplate jdbc;
    @Autowired protected ObjectMapper json;
    @Autowired UserRepository users;
    @Autowired PasswordEncoder encoder;

    @BeforeEach
    void seedUsersAndCleanData() {
        for (Role role : Role.values()) {
            String email = role.name().toLowerCase() + "@test.org";
            if (users.findByEmailIgnoreCase(email).isEmpty()) {
                users.save(new AppUser(email, encoder.encode(PASSWORD), email, EnumSet.of(role)));
            }
        }
        if (users.findByEmailIgnoreCase("revisor2@test.org").isEmpty()) {
            users.save(new AppUser("revisor2@test.org", encoder.encode(PASSWORD), "revisor2@test.org", EnumSet.of(Role.REVISOR)));
        }
        // TRUNCATE não dispara os triggers de imutabilidade; isola os testes entre si.
        jdbc.execute("TRUNCATE protocol, study, document, substance, outbox, audit_log RESTART IDENTITY CASCADE");
    }

    protected String tokenForEmail(String email) throws Exception {
        String body = json.writeValueAsString(Map.of("email", email, "password", PASSWORD));
        String res = mvc.perform(post("/api/auth/login").contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString();
        JsonNode node = json.readTree(res);
        return "Bearer " + node.get("token").asText();
    }

    protected String tokenFor(Role role) throws Exception {
        String body = json.writeValueAsString(Map.of("email", role.name().toLowerCase() + "@test.org", "password", PASSWORD));
        String res = mvc.perform(post("/api/auth/login").contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString();
        JsonNode node = json.readTree(res);
        return "Bearer " + node.get("token").asText();
    }
}

