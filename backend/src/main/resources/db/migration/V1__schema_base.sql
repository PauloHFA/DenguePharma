-- DenguePharma: modelo conceitual (PDF, seção 12).
-- UUIDs internos, timestamps em UTC (timestamptz), nenhuma chave natural por nome de substância.

-- ===== Acesso =====
CREATE TABLE app_user (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         TEXT        NOT NULL,
    password_hash TEXT        NOT NULL,
    display_name  TEXT        NOT NULL,
    active        BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX ux_app_user_email ON app_user (lower(email));

CREATE TABLE user_role (
    user_id UUID NOT NULL REFERENCES app_user (id) ON DELETE CASCADE,
    role    TEXT NOT NULL CHECK (role IN ('LEITOR','REVISOR','ADJUDICADOR','PESQUISADOR','ADMINISTRADOR')),
    PRIMARY KEY (user_id, role)
);

-- ===== Trilha de auditoria (append-only) =====
CREATE TABLE audit_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id    UUID REFERENCES app_user (id),
    action      TEXT        NOT NULL,
    entity_type TEXT        NOT NULL,
    entity_id   TEXT,
    before_data JSONB,
    after_data  JSONB,
    reason      TEXT,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_audit_entity ON audit_log (entity_type, entity_id);

CREATE FUNCTION forbid_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION '% e append-only: % nao permitido', TG_TABLE_NAME, TG_OP;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_log_immutable
    BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION forbid_mutation();

-- ===== Protocolo e buscas (RF-01) =====
CREATE TABLE protocol (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code         TEXT        NOT NULL,
    version      INT         NOT NULL CHECK (version > 0),
    title        TEXT        NOT NULL,
    question     TEXT        NOT NULL,
    sources      JSONB       NOT NULL,
    strategy     JSONB       NOT NULL,
    eligibility  JSONB       NOT NULL,
    cutoff_date  DATE        NOT NULL,
    status       TEXT        NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','REGISTERED','FROZEN')),
    created_by   UUID        REFERENCES app_user (id),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (code, version)
);

CREATE TABLE search_run (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    protocol_id       UUID        NOT NULL REFERENCES protocol (id),
    source            TEXT        NOT NULL,
    query             TEXT        NOT NULL,
    params            JSONB       NOT NULL DEFAULT '{}',
    pagination        JSONB       NOT NULL DEFAULT '{}',
    total_returned    INT,
    connector_version TEXT        NOT NULL,
    api_version       TEXT,
    checkpoint        JSONB,
    executed_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ===== Substâncias =====
CREATE TABLE substance (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    published_name  TEXT        NOT NULL,
    normalized_name TEXT,
    product_type    TEXT,
    is_combination  BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE substance_alias (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    substance_id    UUID NOT NULL REFERENCES substance (id),
    alias           TEXT NOT NULL,
    external_source TEXT,
    external_id     TEXT,
    CHECK ((external_source IS NULL) = (external_id IS NULL))
);
CREATE UNIQUE INDEX ux_substance_alias_external
    ON substance_alias (external_source, external_id) WHERE external_source IS NOT NULL;

-- Combinação tem componentes próprios e nunca é fundida com monoterapia.
CREATE TABLE substance_component (
    combination_id UUID NOT NULL REFERENCES substance (id),
    component_id   UUID NOT NULL REFERENCES substance (id),
    PRIMARY KEY (combination_id, component_id),
    CHECK (combination_id <> component_id)
);

-- ===== Estudos =====
CREATE TABLE study (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title      TEXT,
    design     TEXT,
    phase      TEXT,
    context    TEXT NOT NULL DEFAULT 'HUMANO'
        CHECK (context IN ('HUMANO','DESAFIO_CONTROLADO','IN_SILICO','IN_VITRO','ANIMAL')),
    purpose    TEXT
        CHECK (purpose IN ('PROFILAXIA','TRATAMENTO','MANEJO_SINTOMATICO','OUTRO')),
    status     TEXT NOT NULL DEFAULT 'ATIVO' CHECK (status IN ('ATIVO','RETRATADO')),
    retraction_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (status <> 'RETRATADO' OR retraction_reason IS NOT NULL)
);

CREATE TABLE study_identifier (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    study_id   UUID NOT NULL REFERENCES study (id),
    source     TEXT NOT NULL,
    id_type    TEXT NOT NULL CHECK (id_type IN ('NCT','PMID','PMCID','DOI','OUTRO')),
    value      TEXT NOT NULL,
    -- Identificador externo único por fonte e tipo.
    UNIQUE (source, id_type, value)
);

-- ===== Documentos e versões imutáveis =====
CREATE TABLE document (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_type   TEXT NOT NULL CHECK (doc_type IN ('PUBLICACAO','REGISTRO_ENSAIO','DOCUMENTO_OFICIAL')),
    title      TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE document_version (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id    UUID        NOT NULL REFERENCES document (id),
    version_no     INT         NOT NULL CHECK (version_no > 0),
    content_hash   TEXT        NOT NULL,
    origin         TEXT        NOT NULL,
    license        TEXT,
    access_status  TEXT        NOT NULL DEFAULT 'SOMENTE_RESUMO'
        CHECK (access_status IN ('TEXTO_COMPLETO','SOMENTE_RESUMO','TEXTO_NAO_OBTIDO','AGUARDANDO_TRADUCAO')),
    storage_uri    TEXT,
    retrieved_at   TIMESTAMPTZ NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (document_id, version_no),
    -- Versão de documento única por hash/origem.
    UNIQUE (content_hash, origin)
);

CREATE TRIGGER trg_document_version_immutable
    BEFORE UPDATE OR DELETE ON document_version
    FOR EACH ROW EXECUTE FUNCTION forbid_mutation();

CREATE TABLE study_document (
    study_id        UUID NOT NULL REFERENCES study (id),
    document_id     UUID NOT NULL REFERENCES document (id),
    report_role     TEXT NOT NULL CHECK (report_role IN ('REGISTRO','PUBLICACAO_PRINCIPAL','SEGUIMENTO','SUBGRUPO','EXTENSAO','OUTRO')),
    link_certainty  TEXT NOT NULL CHECK (link_certainty IN ('CONFIRMADO','PROVAVEL','INCERTO')),
    linked_by       UUID REFERENCES app_user (id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (study_id, document_id)
);

-- ===== Braços, intervenções, desfechos e resultados =====
CREATE TABLE arm (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    study_id      UUID    NOT NULL REFERENCES study (id),
    label         TEXT    NOT NULL,
    is_comparator BOOLEAN NOT NULL DEFAULT FALSE,
    n_randomized  INT CHECK (n_randomized >= 0),
    n_analyzed    INT CHECK (n_analyzed >= 0)
);

CREATE TABLE intervention (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    arm_id           UUID NOT NULL REFERENCES arm (id),
    substance_id     UUID NOT NULL REFERENCES substance (id),
    purpose          TEXT NOT NULL CHECK (purpose IN ('PROFILAXIA','TRATAMENTO','MANEJO_SINTOMATICO','OUTRO')),
    timing           TEXT,
    route            TEXT,
    regimen_reported TEXT   -- descrição do protocolo estudado; nunca recomendação de dose.
);

CREATE TABLE outcome (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    study_id       UUID NOT NULL REFERENCES study (id),
    definition     TEXT NOT NULL,
    category       TEXT NOT NULL CHECK (category IN ('CLINICO','VIROLOGICO','SEGURANCA','OUTRO')),
    tier           TEXT NOT NULL CHECK (tier IN ('PRIMARIO','SECUNDARIO','EXPLORATORIO')),
    time_frame     TEXT,
    unit           TEXT,
    population     TEXT
);

-- Resultado não existe sem estudo (via desfecho) e sem proveniência (document_version_id).
CREATE TABLE result (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    outcome_id          UUID NOT NULL REFERENCES outcome (id),
    arm_id              UUID REFERENCES arm (id),
    comparison_arm_id   UUID REFERENCES arm (id),
    document_version_id UUID NOT NULL REFERENCES document_version (id),
    evidence_span_id    UUID,
    effect_measure      TEXT,
    estimate_original   TEXT,
    estimate_normalized NUMERIC,
    ci_low              NUMERIC,
    ci_high             NUMERIC,
    denominator         INT,
    p_value             NUMERIC,
    analysis_population TEXT,
    direction           TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ===== Extração assistida (RF-05) =====
CREATE TABLE extraction_run (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_version_id  UUID        NOT NULL REFERENCES document_version (id),
    pipeline_version     TEXT        NOT NULL,
    model_provider       TEXT        NOT NULL,
    model_version        TEXT        NOT NULL,
    prompt_hash          TEXT        NOT NULL,
    execution_variant    TEXT        NOT NULL DEFAULT 'default',
    schema_version       TEXT        NOT NULL,
    parameters           JSONB       NOT NULL DEFAULT '{}',
    cost_usd             NUMERIC,
    duration_ms          BIGINT,
    status               TEXT        NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING','RUNNING','COMPLETED','FAILED','QUARANTINED')),
    attempts             INT         NOT NULL DEFAULT 0,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Chave de idempotência: document_version_id + pipeline + modelo + prompt + variante.
    UNIQUE (document_version_id, pipeline_version, model_version, prompt_hash, execution_variant)
);

CREATE TABLE evidence_span (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_version_id UUID NOT NULL REFERENCES document_version (id),
    section             TEXT,
    page                INT,
    locator             TEXT NOT NULL,
    text                TEXT NOT NULL
);

ALTER TABLE result
    ADD CONSTRAINT fk_result_span FOREIGN KEY (evidence_span_id) REFERENCES evidence_span (id);

CREATE TABLE extracted_field (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    extraction_run_id UUID NOT NULL REFERENCES extraction_run (id),
    study_id          UUID REFERENCES study (id),
    field_name        TEXT NOT NULL,
    original_value    TEXT,
    normalized_value  TEXT,
    absence_status    TEXT NOT NULL DEFAULT 'PRESENTE'
        CHECK (absence_status IN ('PRESENTE','NAO_INFORMADO','NAO_APLICAVEL','NAO_EXTRAIDO','INCERTO','NAO_HOUVE_EVENTO')),
    evidence_span_id  UUID REFERENCES evidence_span (id),
    review_status     TEXT NOT NULL DEFAULT 'RASCUNHO_IA'
        CHECK (review_status IN ('RASCUNHO_IA','EM_REVISAO','APROVADO','REJEITADO')),
    published         BOOLEAN NOT NULL DEFAULT FALSE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Valor presente exige trecho de suporte (abstenção quando não houver).
    CHECK (absence_status <> 'PRESENTE' OR evidence_span_id IS NOT NULL),
    -- Somente revisão aprovada pode ser publicada.
    CHECK (NOT published OR review_status = 'APROVADO')
);

-- Não sobrescrever valores aprovados com extração automática posterior.
CREATE FUNCTION protect_approved_field() RETURNS trigger AS $$
BEGIN
    IF OLD.review_status = 'APROVADO' AND (
        NEW.original_value   IS DISTINCT FROM OLD.original_value OR
        NEW.normalized_value IS DISTINCT FROM OLD.normalized_value OR
        NEW.absence_status   <> OLD.absence_status OR
        NEW.evidence_span_id IS DISTINCT FROM OLD.evidence_span_id) THEN
        RAISE EXCEPTION 'campo aprovado % nao pode ser sobrescrito; crie nova revisao', OLD.id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_protect_approved_field
    BEFORE UPDATE ON extracted_field
    FOR EACH ROW EXECUTE FUNCTION protect_approved_field();

-- ===== Triagem e revisão (RF-04, RF-06) =====
CREATE TABLE screening_decision (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    study_id         UUID NOT NULL REFERENCES study (id),
    document_id      UUID REFERENCES document (id),
    reviewer_id      UUID NOT NULL REFERENCES app_user (id),
    stage            TEXT NOT NULL CHECK (stage IN ('TITULO_RESUMO','TEXTO_COMPLETO')),
    decision         TEXT NOT NULL CHECK (decision IN ('INCLUIR','EXCLUIR','INCERTO')),
    exclusion_reason TEXT,
    is_adjudication  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (decision <> 'EXCLUIR' OR stage = 'TITULO_RESUMO' OR exclusion_reason IS NOT NULL)
);
-- Decisões individuais são preservadas: sem sobrescrita nem remoção.
CREATE TRIGGER trg_screening_immutable
    BEFORE UPDATE OR DELETE ON screening_decision
    FOR EACH ROW EXECUTE FUNCTION forbid_mutation();

CREATE TABLE review_decision (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    extracted_field_id UUID NOT NULL REFERENCES extracted_field (id),
    reviewer_id        UUID NOT NULL REFERENCES app_user (id),
    decision           TEXT NOT NULL CHECK (decision IN ('ACEITAR','CORRIGIR','REJEITAR')),
    value_before       TEXT,
    value_after        TEXT,
    reason             TEXT,
    is_adjudication    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TRIGGER trg_review_immutable
    BEFORE UPDATE OR DELETE ON review_decision
    FOR EACH ROW EXECUTE FUNCTION forbid_mutation();

-- ===== Outbox / Inbox / Job (seção 13) =====
CREATE TABLE outbox (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id       UUID        NOT NULL UNIQUE,   -- estável entre retentativas
    aggregate_type TEXT        NOT NULL,
    aggregate_id   TEXT        NOT NULL,
    event_type     TEXT        NOT NULL,
    schema_version INT         NOT NULL DEFAULT 1,
    payload        JSONB       NOT NULL,          -- referências, nunca o texto integral
    priority       INT         NOT NULL DEFAULT 0,
    attempts       INT         NOT NULL DEFAULT 0,
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_at   TIMESTAMPTZ
);
CREATE INDEX ix_outbox_pending ON outbox (priority DESC, next_attempt_at) WHERE published_at IS NULL;

CREATE TABLE inbox (
    event_id     UUID        NOT NULL,
    consumer     TEXT        NOT NULL,
    received_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at TIMESTAMPTZ,
    PRIMARY KEY (event_id, consumer)
);

CREATE TABLE job (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type     TEXT        NOT NULL,
    ref_id       TEXT        NOT NULL,
    status       TEXT        NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING','LEASED','COMPLETED','FAILED','QUARANTINED')),
    lease_token  UUID,
    lease_until  TIMESTAMPTZ,
    attempts     INT         NOT NULL DEFAULT 0,
    max_attempts INT         NOT NULL DEFAULT 5,
    last_error   TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ===== Relatórios (RF-09) =====
CREATE TABLE report_snapshot (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requested_by UUID REFERENCES app_user (id),
    filters      JSONB       NOT NULL,
    data         JSONB       NOT NULL,
    refs         JSONB       NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TRIGGER trg_report_snapshot_immutable
    BEFORE UPDATE OR DELETE ON report_snapshot
    FOR EACH ROW EXECUTE FUNCTION forbid_mutation();

