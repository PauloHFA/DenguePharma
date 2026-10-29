ALTER TABLE outbox ADD COLUMN relay_token UUID, ADD COLUMN relay_until TIMESTAMPTZ,
    ADD COLUMN last_error TEXT;
-- Preserva bytes canonicos antes da normalizacao numerica/chaves feita pelo JSONB.
ALTER TABLE document_version ADD COLUMN canonical_content TEXT;
ALTER TABLE job ADD COLUMN source_event_id UUID UNIQUE REFERENCES outbox(event_id),
    ADD COLUMN next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ADD COLUMN extraction_run_id UUID REFERENCES extraction_run(id);
CREATE TABLE document_archive (
    document_version_id UUID PRIMARY KEY REFERENCES document_version(id),
    storage_uri TEXT NOT NULL, content_hash TEXT NOT NULL,
    size_bytes BIGINT NOT NULL CHECK (size_bytes > 0), verified_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TRIGGER trg_document_archive_immutable BEFORE UPDATE OR DELETE ON document_archive
    FOR EACH ROW EXECUTE FUNCTION forbid_mutation();
CREATE TABLE report_artifact (
    report_snapshot_id UUID NOT NULL REFERENCES report_snapshot(id),
    format TEXT NOT NULL CHECK (format IN ('pdf','csv','json')),
    content_hash TEXT NOT NULL, storage_uri TEXT NOT NULL, size_bytes BIGINT NOT NULL CHECK (size_bytes > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), PRIMARY KEY (report_snapshot_id, format)
);
CREATE TRIGGER trg_report_artifact_immutable BEFORE UPDATE OR DELETE ON report_artifact
    FOR EACH ROW EXECUTE FUNCTION forbid_mutation();
