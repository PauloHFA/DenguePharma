-- V4: Fila de reavaliação por mudança de fonte (RF-10), campos de catálogo/comparação com regras científicas
-- (RC-01 a RC-07, RF-07, RF-08) e retratação que preserva histórico e invalida síntese vigente (T6).

-- ===== Fila de reavaliação quando a fonte muda ou há errata/retratação (RF-10, RC-06) =====
CREATE TABLE reassessment_task (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    study_id            UUID        NOT NULL REFERENCES study (id),
    document_version_id UUID        REFERENCES document_version (id),
    trigger_type        TEXT        NOT NULL CHECK (trigger_type IN ('FONTE_ALTERADA','ERRATA','RETRATACAO')),
    status              TEXT        NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','RESOLVED')),
    notes               TEXT,
    resolved_by         UUID        REFERENCES app_user (id),
    resolved_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_reassessment_status ON reassessment_task (status);

-- ===== Atributos estruturados de síntese do estudo (alimentados após revisão aprovada, RF-07, RF-08, RC-01..07) =====
ALTER TABLE study
    ADD COLUMN serotype               TEXT,
    ADD COLUMN countries              TEXT,
    ADD COLUMN sample_size            INT CHECK (sample_size IS NULL OR sample_size >= 0),
    ADD COLUMN comparator_label       TEXT,
    ADD COLUMN outcome_summary        TEXT,
    ADD COLUMN outcome_category       TEXT CHECK (outcome_category IS NULL OR outcome_category IN ('CLINICO','VIROLOGICO','SEGURANCA','OUTRO')),
    ADD COLUMN outcome_time_frame     TEXT,
    ADD COLUMN effect_summary         TEXT,
    ADD COLUMN adverse_events_status  TEXT NOT NULL DEFAULT 'NAO_INFORMADO'
        CHECK (adverse_events_status IN ('RELATADOS','AUSENCIA_DE_RELATO','NAO_HOUVE_EVENTO','NAO_INFORMADO')),
    ADD COLUMN limitations            TEXT NOT NULL DEFAULT 'Evidência sujeita às limitações metodológicas do estudo primário.',
    ADD COLUMN risk_of_bias_tool      TEXT CHECK (risk_of_bias_tool IS NULL OR risk_of_bias_tool IN ('ROB2','ROBINS_I','NAO_APLICAVEL','NAO_AVALIADO')),
    ADD COLUMN risk_of_bias_level     TEXT CHECK (risk_of_bias_level IS NULL OR risk_of_bias_level IN ('BAIXO','ALGUMAS_PREOCUPACOES','ALTO','INCERTO')),
    ADD COLUMN regulatory_status      TEXT NOT NULL DEFAULT 'CANDIDATO_EM_PESQUISA'
        CHECK (regulatory_status IN ('CANDIDATO_EM_PESQUISA','APROVADO_OUTRA_INDICACAO','APROVADO_DENGUE')),
    ADD COLUMN regulatory_authority   TEXT,
    ADD COLUMN regulatory_jurisdiction TEXT,
    ADD COLUMN regulatory_indication  TEXT,
    ADD COLUMN regulatory_source      TEXT,
    ADD COLUMN regulatory_date        DATE,
    ADD COLUMN retracted_at           TIMESTAMPTZ,
    -- RC-02: Toda alegação regulatória de aprovação exige autoridade, jurisdição, indicação, fonte e data.
    ADD CONSTRAINT chk_regulatory_claim CHECK (
        regulatory_status = 'CANDIDATO_EM_PESQUISA' OR (
            regulatory_authority IS NOT NULL AND
            regulatory_jurisdiction IS NOT NULL AND
            regulatory_indication IS NOT NULL AND
            regulatory_source IS NOT NULL AND
            regulatory_date IS NOT NULL
        )
    ),
    -- RC-05: RoB 2 nunca pode ser aplicado indiscriminadamente a desenhos não-randomizados.
    ADD CONSTRAINT chk_rob2_design CHECK (
        risk_of_bias_tool IS DISTINCT FROM 'ROB2' OR design = 'ENSAIO_RANDOMIZADO'
    );

-- Relacionamento direto de estudo com substância principal estudada para o catálogo (além de arm/intervention).
ALTER TABLE study ADD COLUMN primary_substance_id UUID REFERENCES substance (id);
