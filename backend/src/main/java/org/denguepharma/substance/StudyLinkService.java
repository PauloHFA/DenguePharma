package org.denguepharma.substance;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.denguepharma.audit.AuditService;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

/**
 * RF-03 e Cenário T3: Propor vínculos de estudo; fusão ambígua exige revisão humana e pode ser desfeita
 * restaurando exatamente os vínculos e identificadores originais.
 */
@Service
public class StudyLinkService {

    public record ProposeRequest(UUID primaryStudyId, UUID candidateStudyId, String sharedIdentifier,
                                 String idType, String reason) {}

    private final JdbcTemplate jdbc;
    private final ObjectMapper om;
    private final AuditService audit;

    public StudyLinkService(JdbcTemplate jdbc, ObjectMapper om, AuditService audit) {
        this.jdbc = jdbc;
        this.om = om;
        this.audit = audit;
    }

    public List<Map<String, Object>> listProposals() {
        return jdbc.queryForList("""
                select p.id, p.primary_study_id, s1.title as primary_title,
                       p.candidate_study_id, s2.title as candidate_title,
                       p.shared_identifier, p.id_type, p.reason, p.status,
                       p.created_at, p.decided_at, p.undone_at
                from study_link_proposal p
                join study s1 on s1.id = p.primary_study_id
                join study s2 on s2.id = p.candidate_study_id
                order by p.created_at desc
                """);
    }

    @Transactional
    public Map<String, Object> propose(ProposeRequest req, UUID actor) {
        if (req.primaryStudyId().equals(req.candidateStudyId())) {
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, "estudos devem ser distintos");
        }
        UUID id = UUID.randomUUID();
        jdbc.update("""
                insert into study_link_proposal (id, primary_study_id, candidate_study_id, shared_identifier, id_type, reason)
                values (?, ?, ?, ?, ?, ?)
                """, id, req.primaryStudyId(), req.candidateStudyId(), req.sharedIdentifier(), req.idType(), req.reason());
        audit.record(actor, "STUDY_LINK_PROPOSED", "study_link_proposal", id.toString(), null, null, req.reason());
        return Map.of("id", id, "status", "PENDING");
    }

    /** Aprova a fusão: vincula os documentos e identificadores do estudo candidato ao principal, guardando snapshot para desfazer. */
    @Transactional
    public void approve(UUID proposalId, String reportRole, UUID actor) {
        List<Map<String, Object>> rows = jdbc.queryForList(
                "select * from study_link_proposal where id = ?", proposalId);
        if (rows.isEmpty()) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "proposta nao encontrada");
        Map<String, Object> p = rows.get(0);
        if (!"PENDING".equals(p.get("status"))) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "proposta nao esta pendente");
        }
        UUID primaryId = (UUID) p.get("primary_study_id");
        UUID candidateId = (UUID) p.get("candidate_study_id");

        ObjectNode snapshot = om.createObjectNode();
        String prevStatus = jdbc.queryForObject("select screening_status from study where id = ?", String.class, candidateId);
        snapshot.put("candidate_prev_screening_status", prevStatus);

        // Fotografa documentos e identificadores que serão movidos para permitir reversão exata.
        List<Map<String, Object>> candDocs = jdbc.queryForList(
                "select document_id, report_role, link_certainty from study_document where study_id = ?", candidateId);
        ArrayNode movedDocs = snapshot.putArray("moved_documents");
        String roleToUse = (reportRole == null || reportRole.isBlank()) ? "PUBLICACAO_PRINCIPAL" : reportRole;
        for (Map<String, Object> d : candDocs) {
            UUID docId = (UUID) d.get("document_id");
            Boolean alreadyInPrimary = jdbc.queryForObject(
                    "select exists (select 1 from study_document where study_id = ? and document_id = ?)",
                    Boolean.class, primaryId, docId);
            if (!Boolean.TRUE.equals(alreadyInPrimary)) {
                jdbc.update("""
                        insert into study_document (study_id, document_id, report_role, link_certainty, linked_by)
                        values (?, ?, ?, 'CONFIRMADO', ?)
                        """, primaryId, docId, roleToUse, actor);
                movedDocs.add(docId.toString());
            }
        }

        List<UUID> candIdentifiers = jdbc.queryForList(
                "select id from study_identifier where study_id = ?", UUID.class, candidateId);
        ArrayNode movedIds = snapshot.putArray("moved_identifiers");
        for (UUID sid : candIdentifiers) {
            jdbc.update("update study_identifier set study_id = ? where id = ?", primaryId, sid);
            movedIds.add(sid.toString());
        }

        jdbc.update("update study set merged_into_id = ?, screening_status = 'FUSAO_ABSORVIDO' where id = ?",
                primaryId, candidateId);
        jdbc.update("""
                update study_link_proposal
                set status = 'APPROVED', snapshot_before = ?::jsonb, decided_by = ?, decided_at = now()
                where id = ?
                """, write(snapshot), actor, proposalId);
        audit.record(actor, "STUDY_MERGE_APPROVED", "study_link_proposal", proposalId.toString(),
                null, write(snapshot), null);
    }

    @Transactional
    public void reject(UUID proposalId, String reason, UUID actor) {
        int n = jdbc.update("""
                update study_link_proposal set status = 'REJECTED', decided_by = ?, decided_at = now()
                where id = ? and status = 'PENDING'
                """, actor, proposalId);
        if (n == 0) throw new ResponseStatusException(HttpStatus.CONFLICT, "proposta nao esta pendente");
        audit.record(actor, "STUDY_MERGE_REJECTED", "study_link_proposal", proposalId.toString(), null, null, reason);
    }

    /** Desfaz uma fusão aprovada (RF-03), restaurando os identificadores, documentos e status do estudo candidato. */
    @Transactional
    public void undo(UUID proposalId, String reason, UUID actor) {
        List<Map<String, Object>> rows = jdbc.queryForList(
                "select * from study_link_proposal where id = ?", proposalId);
        if (rows.isEmpty()) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "proposta nao encontrada");
        Map<String, Object> p = rows.get(0);
        if (!"APPROVED".equals(p.get("status"))) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "somente fusao aprovada pode ser desfeita");
        }
        UUID primaryId = (UUID) p.get("primary_study_id");
        UUID candidateId = (UUID) p.get("candidate_study_id");
        JsonNode snap = read(String.valueOf(p.get("snapshot_before")));

        for (JsonNode docIdNode : snap.path("moved_documents")) {
            jdbc.update("delete from study_document where study_id = ? and document_id = ?::uuid",
                    primaryId, docIdNode.asText());
        }
        for (JsonNode idNode : snap.path("moved_identifiers")) {
            jdbc.update("update study_identifier set study_id = ? where id = ?::uuid",
                    candidateId, idNode.asText());
        }
        String prevStatus = snap.path("candidate_prev_screening_status").asText("AGUARDANDO_TITULO_RESUMO");
        jdbc.update("update study set merged_into_id = null, screening_status = ? where id = ?",
                prevStatus, candidateId);
        jdbc.update("""
                update study_link_proposal set status = 'UNDONE', undone_by = ?, undone_at = now()
                where id = ?
                """, actor, proposalId);
        audit.record(actor, "STUDY_MERGE_UNDONE", "study_link_proposal", proposalId.toString(),
                write(snap), null, reason);
    }

    private String write(Object o) {
        try {
            return om.writeValueAsString(o);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException(e);
        }
    }

    private JsonNode read(String s) {
        try {
            return om.readTree(s);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException(e);
        }
    }
}

