package org.denguepharma.analysis;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.*;

import java.util.*;

/**
 * Endpoint publico para consulta de bioatividades farmacologicas ChEMBL e alvos moleculares (REQ-IDN-002, OE1).
 */
@RestController
@RequestMapping("/api/public")
public class BioactivityController {

    private final JdbcTemplate jdbc;

    public BioactivityController(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public record BioactivityDTO(
            UUID id,
            String substanceName,
            String chemblAssayId,
            String targetName,
            String targetOrganism,
            String activityType,
            Double activityValue,
            String activityUnits,
            String relation
    ) {}

    @GetMapping("/bioactivities")
    public List<BioactivityDTO> listBioactivities(@RequestParam(required = false) String target,
                                                  @RequestParam(required = false) String substance) {
        StringBuilder sql = new StringBuilder("""
                select ba.id, s.published_name as substance_name, ba.chembl_assay_id,
                       ba.target_name, ba.target_organism, ba.activity_type,
                       ba.activity_value, ba.activity_units, ba.relation
                from substance_bioactivity ba
                join substance s on s.id = ba.substance_id
                where 1=1
                """);
        List<Object> params = new ArrayList<>();

        if (target != null && !target.isBlank()) {
            sql.append(" and lower(ba.target_name) like ?");
            params.add("%" + target.toLowerCase().trim() + "%");
        }
        if (substance != null && !substance.isBlank()) {
            sql.append(" and (lower(s.published_name) like ? or lower(s.normalized_name) like ?)");
            params.add("%" + substance.toLowerCase().trim() + "%");
            params.add("%" + substance.toLowerCase().trim() + "%");
        }
        sql.append(" order by ba.activity_value asc");

        return jdbc.query(sql.toString(), (rs, i) -> new BioactivityDTO(
                rs.getObject("id", UUID.class),
                rs.getString("substance_name"),
                rs.getString("chembl_assay_id"),
                rs.getString("target_name"),
                rs.getString("target_organism"),
                rs.getString("activity_type"),
                rs.getObject("activity_value") != null ? rs.getDouble("activity_value") : null,
                rs.getString("activity_units"),
                rs.getString("relation")
        ), params.toArray());
    }
}
