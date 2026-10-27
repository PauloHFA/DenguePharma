-- V3: Propostas de fusão/vínculo de estudos com reversão (RF-03, T3)
-- e controle de elegibilidade / triagem independente + adjudicação (RF-04, Seção 07).

-- ===== Propostas de vínculo/fusão entre estudos (RF-03, T3) =====
CREATE TABLE study_link_proposal (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    primary_study_id  UUID        NOT NULL REFERENCES study (id),
    candidate_study_id UUID       NOT NULL REFERENCES study (id),
    shared_identifier TEXT        NOT NULL,
    id_type           TEXT        NOT NULL,
    reason            TEXT        NOT NULL,
    status            TEXT        NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING','APPROVED','REJECTED','UNDONE')),
    snapshot_before   JSONB       NOT NULL DEFAULT '{}',
    decided_by        UUID        REFERENCES app_user (id),
    decided_at        TIMESTAMPTZ,
    undone_by         UUID        REFERENCES app_user (id),
    undone_at         TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (primary_study_id <> candidate_study_id)
);
CREATE INDEX ix_study_link_proposal_status ON study_link_proposal (status);

-- Estudo absorvido em fusão aprovada aponta para o estudo principal sem apagar histórico (pode ser desfeito).
ALTER TABLE study
    ADD COLUMN merged_into_id UUID REFERENCES study (id),
    ADD COLUMN screening_status TEXT NOT NULL DEFAULT 'AGUARDANDO_TITULO_RESUMO'
        CHECK (screening_status IN (
            'AGUARDANDO_TITULO_RESUMO',
            'DIVERGENCIA_TITULO_RESUMO',
            'AGUARDANDO_TEXTO_COMPLETO',
            'DIVERGENCIA_TEXTO_COMPLETO',
            'INCLUIDO_NUCLEO',
            'INCLUIDO_SEM_RESULTADO',
            'CAMADA_COMPLEMENTAR',
            'EXCLUIDO',
            'FUSAO_ABSORVIDO'
        )),
    ADD COLUMN exclusion_category TEXT
        CHECK (exclusion_category IS NULL OR exclusion_category IN (
            'REVISAO_EDITORIAL_NOTICIA',
            'VACINA',
            'CONTROLE_VETOR',
            'DIAGNOSTICO_ISOLADO',
            'DOENCA_DISTINTA',
            'PRE_CLINICO',
            'DUPLICADO',
            'OUTRO'
        )),
    ADD COLUMN final_exclusion_reason TEXT;

-- Um mesmo revisor não pode registrar duas decisões não-adjudicadoras na mesma etapa para o mesmo estudo.
CREATE UNIQUE INDEX ux_screening_reviewer_stage
    ON screening_decision (study_id, reviewer_id, stage)
    WHERE is_adjudication = FALSE;
