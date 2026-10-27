package org.denguepharma.substance;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.denguepharma.audit.AuditService;
import org.denguepharma.ingest.HttpSupport;
import org.denguepharma.ingest.IngestProperties;
import org.denguepharma.substance.PubChemClient.PubChemEntry;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

/**
 * RF-03: Normaliza substâncias e gerencia combinações separadas de monoterapia (Seção 12).
 * Nunca usa o nome da substância como chave primária ou única.
 */
@Service
public class SubstanceService {

    public record SubstanceInput(String publishedName, String productType, boolean combination,
                                 List<UUID> componentIds) {}

    public record SubstanceView(UUID id, String publishedName, String normalizedName, String productType,
                                boolean combination, List<Map<String, Object>> aliases, List<UUID> componentIds) {}

    private final JdbcTemplate jdbc;
    private final AuditService audit;
    private final PubChemClient pubChem;

    @Autowired
    public SubstanceService(JdbcTemplate jdbc, AuditService audit, IngestProperties ingestProps, ObjectMapper om,
                            @Value("${denguepharma.pubchem.base-url:https://pubchem.ncbi.nlm.nih.gov/rest/pug}") String pubchemUrl) {
        this(jdbc, audit, new PubChemClient(pubchemUrl, HttpSupport.standard(ingestProps.userAgent(), 220), om));
    }

    public SubstanceService(JdbcTemplate jdbc, AuditService audit, PubChemClient pubChem) {
        this.jdbc = jdbc;
        this.audit = audit;
        this.pubChem = pubChem;
    }

    public List<SubstanceView> list() {
        List<UUID> ids = jdbc.queryForList("select id from substance order by created_at desc", UUID.class);
        return ids.stream().map(this::get).toList();
    }

    public SubstanceView get(UUID id) {
        List<Map<String, Object>> rows = jdbc.queryForList(
                "select id, published_name, normalized_name, product_type, is_combination from substance where id = ?", id);
        if (rows.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "substancia nao encontrada");
        }
        Map<String, Object> r = rows.get(0);
        List<Map<String, Object>> aliases = jdbc.queryForList(
                "select id, alias, external_source, external_id from substance_alias where substance_id = ? order by alias", id);
        List<UUID> components = jdbc.queryForList(
                "select component_id from substance_component where combination_id = ?", UUID.class, id);
        return new SubstanceView((UUID) r.get("id"), (String) r.get("published_name"),
                (String) r.get("normalized_name"), (String) r.get("product_type"),
                Boolean.TRUE.equals(r.get("is_combination")), aliases, components);
    }

    @Transactional
    public SubstanceView create(SubstanceInput in, UUID actor) {
        if (in.combination() && (in.componentIds() == null || in.componentIds().size() < 2)) {
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,
                    "combinacao exige ao menos 2 componentes separados e nao pode ser fundida com monoterapia");
        }
        if (!in.combination() && in.componentIds() != null && !in.componentIds().isEmpty()) {
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,
                    "monoterapia nao pode ter componentes de combinacao");
        }
        UUID id = UUID.randomUUID();
        jdbc.update("insert into substance (id, published_name, product_type, is_combination) values (?, ?, ?, ?)",
                id, in.publishedName().trim(), in.productType(), in.combination());
        jdbc.update("insert into substance_alias (substance_id, alias) values (?, ?)", id, in.publishedName().trim());
        if (in.combination()) {
            for (UUID compId : in.componentIds()) {
                Boolean compIsCombo = jdbc.queryForObject(
                        "select is_combination from substance where id = ?", Boolean.class, compId);
                if (Boolean.TRUE.equals(compIsCombo)) {
                    throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,
                            "componente deve ser substancia individual");
                }
                jdbc.update("insert into substance_component (combination_id, component_id) values (?, ?)", id, compId);
            }
        }
        audit.record(actor, "SUBSTANCE_CREATED", "substance", id.toString(), null,
                "{\"publishedName\":\"" + in.publishedName().replace("\"", "") + "\",\"combination\":" + in.combination() + "}", null);
        return get(id);
    }

    /** Consulta PubChem PUG REST para preencher nome normalizado, CID e sinônimos. */
    @Transactional
    public SubstanceView normalizeWithPubChem(UUID id, UUID actor) {
        SubstanceView s = get(id);
        if (s.combination()) {
            throw new ResponseStatusException(HttpStatus.CONFLICT,
                    "combinacoes sao normalizadas por seus componentes individuais, nunca fundidas com monoterapia");
        }
        Optional<PubChemEntry> entry;
        try {
            entry = pubChem.lookupByName(s.publishedName());
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "consulta PubChem interrompida");
        } catch (IOException e) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "falha ao consultar PubChem: " + e.getMessage());
        }
        if (entry.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "substancia nao localizada no PubChem");
        }
        PubChemEntry p = entry.get();

        // Verifica se outro registro já detém este CID (evita duplicidade silenciosa e sugere revisão).
        List<UUID> existingOwner = jdbc.queryForList(
                "select substance_id from substance_alias where external_source = 'PUBCHEM_CID' and external_id = ?",
                UUID.class, p.cid());
        if (!existingOwner.isEmpty() && !existingOwner.get(0).equals(id)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT,
                    "CID " + p.cid() + " ja vinculado a outra substancia (" + existingOwner.get(0) + ")");
        }

        jdbc.update("update substance set normalized_name = ? where id = ?", p.normalizedName(), id);
        if (existingOwner.isEmpty()) {
            jdbc.update("insert into substance_alias (substance_id, alias, external_source, external_id) values (?, ?, 'PUBCHEM_CID', ?)",
                    id, p.normalizedName(), p.cid());
        }
        for (String syn : p.synonyms()) {
            Boolean exists = jdbc.queryForObject(
                    "select exists (select 1 from substance_alias where substance_id = ? and lower(alias) = lower(?))",
                    Boolean.class, id, syn);
            if (!Boolean.TRUE.equals(exists)) {
                jdbc.update("insert into substance_alias (substance_id, alias) values (?, ?)", id, syn);
            }
        }
        audit.record(actor, "SUBSTANCE_NORMALIZED", "substance", id.toString(), null,
                "{\"cid\":\"" + p.cid() + "\",\"normalizedName\":\"" + p.normalizedName().replace("\"", "") + "\"}", null);
        return get(id);
    }
}
