package org.denguepharma.protocol;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.core.JsonProcessingException;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import org.denguepharma.audit.AuditService;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

/** RF-01: protocolo com fontes, estratégia, elegibilidade e data de corte, versionado e imutável após o registro. */
@Service
public class ProtocolService {

    public static final Set<String> SOURCES = Set.of(
            "PUBMED", "CLINICALTRIALS", "EUROPE_PMC", "PMC_OA", "LILACS", "WHO_ICTRP");

    public record ProtocolInput(String code, String title, String question, JsonNode sources,
                                JsonNode strategy, JsonNode eligibility, LocalDate cutoffDate) {}

    public record ProtocolView(UUID id, String code, int version, String title, String question,
                               JsonNode sources, JsonNode strategy, JsonNode eligibility,
                               LocalDate cutoffDate, String status, java.time.Instant createdAt) {}

    private final JdbcTemplate jdbc;
    private final ObjectMapper om;
    private final AuditService audit;

    public ProtocolService(JdbcTemplate jdbc, ObjectMapper om, AuditService audit) {
        this.jdbc = jdbc;
        this.om = om;
        this.audit = audit;
    }

    private final RowMapper<ProtocolView> mapper = (rs, i) -> new ProtocolView(
            rs.getObject("id", UUID.class), rs.getString("code"), rs.getInt("version"),
            rs.getString("title"), rs.getString("question"),
            json(rs.getString("sources")), json(rs.getString("strategy")), json(rs.getString("eligibility")),
            rs.getObject("cutoff_date", LocalDate.class), rs.getString("status"),
            rs.getObject("created_at", OffsetDateTime.class).toInstant());

    public List<ProtocolView> list() {
        return jdbc.query("select * from protocol order by code, version desc", mapper);
    }

    public ProtocolView get(UUID id) {
        return jdbc.query("select * from protocol where id = ?", mapper, id).stream().findFirst()
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "protocolo nao encontrado"));
    }

    @Transactional
    public ProtocolView create(ProtocolInput in, UUID actor) {
        UUID id = UUID.randomUUID();
        try {
            insert(id, in.code(), 1, in, actor);
        } catch (DuplicateKeyException e) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "codigo de protocolo ja existe");
        }
        audit.record(actor, "PROTOCOL_CREATED", "protocol", id.toString(), null, str(summary(in.code(), 1)), null);
        return get(id);
    }

    @Transactional
    public ProtocolView update(UUID id, ProtocolInput in, UUID actor) {
        ProtocolView current = get(id);
        if (!"DRAFT".equals(current.status())) {
            throw new ResponseStatusException(HttpStatus.CONFLICT,
                    "protocolo registrado e imutavel: crie uma nova versao");
        }
        jdbc.update("""
                update protocol set title = ?, question = ?, sources = ?::jsonb, strategy = ?::jsonb,
                       eligibility = ?::jsonb, cutoff_date = ? where id = ? and status = 'DRAFT'
                """, in.title(), in.question(), str(in.sources()), str(in.strategy()), str(in.eligibility()),
                in.cutoffDate(), id);
        audit.record(actor, "PROTOCOL_UPDATED", "protocol", id.toString(), null, null, null);
        return get(id);
    }

    /** Registra a versão: a partir daqui o conteúdo não pode mais mudar (garantido também por trigger). */
    @Transactional
    public ProtocolView register(UUID id, UUID actor) {
        ProtocolView p = get(id);
        if (!"DRAFT".equals(p.status())) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "protocolo ja registrado");
        }
        List<String> problems = validate(p);
        if (!problems.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, String.join("; ", problems));
        }
        jdbc.update("update protocol set status = 'REGISTERED' where id = ? and status = 'DRAFT'", id);
        audit.record(actor, "PROTOCOL_REGISTERED", "protocol", id.toString(), null,
                str(summary(p.code(), p.version())), null);
        return get(id);
    }

    /** Congela os critérios antes da avaliação final. */
    @Transactional
    public ProtocolView freeze(UUID id, UUID actor) {
        ProtocolView p = get(id);
        if (!"REGISTERED".equals(p.status())) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "apenas protocolo registrado pode ser congelado");
        }
        jdbc.update("update protocol set status = 'FROZEN' where id = ? and status = 'REGISTERED'", id);
        audit.record(actor, "PROTOCOL_FROZEN", "protocol", id.toString(), null, null, null);
        return get(id);
    }

    /** Cria rascunho da próxima versão a partir de uma versão existente. */
    @Transactional
    public ProtocolView newVersion(UUID id, String reason, UUID actor) {
        ProtocolView base = get(id);
        Integer max = jdbc.queryForObject("select max(version) from protocol where code = ?", Integer.class, base.code());
        int next = (max == null ? 0 : max) + 1;
        UUID newId = UUID.randomUUID();
        try {
            insert(newId, base.code(), next, new ProtocolInput(base.code(), base.title(), base.question(),
                    base.sources(), base.strategy(), base.eligibility(), base.cutoffDate()), actor);
        } catch (DuplicateKeyException e) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "outra versao foi criada simultaneamente");
        }
        audit.record(actor, "PROTOCOL_NEW_VERSION", "protocol", newId.toString(),
                str(summary(base.code(), base.version())), str(summary(base.code(), next)), reason);
        return get(newId);
    }

    public List<String> validate(ProtocolView p) {
        List<String> problems = new ArrayList<>();
        if (blank(p.title())) problems.add("titulo obrigatorio");
        if (blank(p.question())) problems.add("pergunta de pesquisa obrigatoria");
        if (p.cutoffDate() == null) problems.add("data de corte obrigatoria");
        if (p.eligibility() == null || !p.eligibility().isObject() || p.eligibility().isEmpty()) {
            problems.add("criterios de elegibilidade obrigatorios");
        }
        if (p.sources() == null || !p.sources().isArray() || p.sources().isEmpty()) {
            problems.add("ao menos uma fonte obrigatoria");
        } else {
            for (JsonNode s : p.sources()) {
                String name = s.asText();
                if (!SOURCES.contains(name)) {
                    problems.add("fonte desconhecida: " + name);
                } else if ("PUBMED".equals(name) && blank(p.strategy().path("pubmed").path("query").asText(null))) {
                    problems.add("estrategia PubMed (strategy.pubmed.query) obrigatoria");
                } else if ("CLINICALTRIALS".equals(name)
                        && blank(p.strategy().path("clinicaltrials").path("condition").asText(null))) {
                    problems.add("estrategia ClinicalTrials.gov (strategy.clinicaltrials.condition) obrigatoria");
                }
            }
        }
        return problems;
    }

    private void insert(UUID id, String code, int version, ProtocolInput in, UUID actor) {
        jdbc.update("""
                insert into protocol (id, code, version, title, question, sources, strategy, eligibility,
                                      cutoff_date, created_by)
                values (?, ?, ?, ?, ?, ?::jsonb, ?::jsonb, ?::jsonb, ?, ?)
                """, id, code, version, in.title(), in.question(), str(in.sources()), str(in.strategy()),
                str(in.eligibility()), in.cutoffDate(), actor);
    }

    private static boolean blank(String s) {
        return s == null || s.isBlank();
    }

    private java.util.Map<String, Object> summary(String code, int version) {
        return java.util.Map.of("code", code, "version", version);
    }

    private String str(Object o) {
        try {
            return om.writeValueAsString(o);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException(e);
        }
    }

    private JsonNode json(String s) {
        try {
            return om.readTree(s);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException(e);
        }
    }
}

