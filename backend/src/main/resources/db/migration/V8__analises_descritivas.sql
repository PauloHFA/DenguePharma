CREATE TABLE analysis_snapshot (
    id UUID PRIMARY KEY,
    requested_by UUID REFERENCES app_user(id),
    filters JSONB NOT NULL,
    dictionary_version TEXT NOT NULL,
    dataset JSONB NOT NULL,
    canonical_content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TRIGGER trg_analysis_snapshot_immutable BEFORE UPDATE OR DELETE ON analysis_snapshot
    FOR EACH ROW EXECUTE FUNCTION forbid_mutation();
CREATE TABLE analysis_run (
    id UUID PRIMARY KEY,
    snapshot_id UUID NOT NULL UNIQUE REFERENCES analysis_snapshot(id),
    source_event_id UUID NOT NULL UNIQUE REFERENCES outbox(event_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TRIGGER trg_analysis_run_immutable BEFORE UPDATE OR DELETE ON analysis_run
    FOR EACH ROW EXECUTE FUNCTION forbid_mutation();
CREATE TABLE analysis_artifact (
    analysis_id UUID NOT NULL REFERENCES analysis_run(id),
    name TEXT NOT NULL,
    media_type TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    storage_uri TEXT NOT NULL,
    content BYTEA NOT NULL CHECK (octet_length(content) <= 33554432),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (analysis_id, name)
);
CREATE TRIGGER trg_analysis_artifact_immutable BEFORE UPDATE OR DELETE ON analysis_artifact
    FOR EACH ROW EXECUTE FUNCTION forbid_mutation();
