-- Proveniencia de cada coleta, inclusive registros reencontrados sem nova versao.
CREATE TABLE search_run_document (
    search_run_id UUID NOT NULL REFERENCES search_run(id),
    document_version_id UUID NOT NULL REFERENCES document_version(id),
    PRIMARY KEY(search_run_id, document_version_id)
);
CREATE TRIGGER trg_search_run_document_immutable BEFORE UPDATE OR DELETE ON search_run_document
    FOR EACH ROW EXECUTE FUNCTION forbid_mutation();

-- Publicar e uma decisao explicita; concluir um job nao publica seus dados.
CREATE TABLE analysis_publication (
    analysis_id UUID PRIMARY KEY REFERENCES analysis_run(id),
    published_by UUID NOT NULL REFERENCES app_user(id),
    published_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TRIGGER trg_analysis_publication_immutable BEFORE UPDATE OR DELETE ON analysis_publication
    FOR EACH ROW EXECUTE FUNCTION forbid_mutation();
