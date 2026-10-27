package org.denguepharma.audit;

import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

/** Escreve na trilha append-only (audit_log). */
@Service
public class AuditService {

    private final JdbcTemplate jdbc;

    public AuditService(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public void record(UUID actorId, String action, String entityType, String entityId,
                       String beforeJson, String afterJson, String reason) {
        jdbc.update("""
                INSERT INTO audit_log (actor_id, action, entity_type, entity_id, before_data, after_data, reason)
                VALUES (?, ?, ?, ?, ?::jsonb, ?::jsonb, ?)
                """, actorId, action, entityType, entityId, beforeJson, afterJson, reason);
    }
}

