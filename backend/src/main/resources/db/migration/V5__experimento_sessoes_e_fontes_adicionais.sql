-- V5: Desenho experimental crossover A/B/C, partição estratificada por família de estudo (25/25/50),
-- ablação offline H3 e cronometragem de sessões de revisão com pausas (Seções 15, 16 e 17 / Entrega E5).

-- ===== Partição experimental por família de estudo (unidade de independência estatística) =====
CREATE TABLE study_family_partition (
    study_id        UUID PRIMARY KEY REFERENCES study (id) ON DELETE CASCADE,
    family_key      TEXT        NOT NULL,
    split_bucket    TEXT        NOT NULL CHECK (split_bucket IN ('DEV','VAL','TEST_FROZEN')),
    stratum         TEXT        NOT NULL DEFAULT 'GERAL',
    frozen_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_study_family_partition_bucket ON study_family_partition (split_bucket);

-- ===== Alocação experimental crossover em blocos balanceados (Condições A, B, C e Ablação H3) =====
-- Regra Seção 15: O mesmo revisor não avalia o mesmo documento nas duas condições (UNIQUE document_version_id, reviewer_id).
CREATE TABLE experiment_allocation (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    study_id            UUID        NOT NULL REFERENCES study (id),
    document_version_id UUID        NOT NULL REFERENCES document_version (id),
    reviewer_id         UUID        NOT NULL REFERENCES app_user (id),
    condition_code      TEXT        NOT NULL CHECK (condition_code IN ('A_MANUAL','B_RULES','C_AI_ASSISTED','H3_NO_SPAN_ABSTENTION')),
    block_code          TEXT        NOT NULL,
    presentation_order  INT         NOT NULL CHECK (presentation_order > 0),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (document_version_id, reviewer_id),
    UNIQUE (document_version_id, condition_code)
);

-- ===== Sessão cronometrada de leitura, verificação, correção e conclusão com pausas (Seção 15 e 16) =====
CREATE TABLE review_timing_session (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    allocation_id           UUID        REFERENCES experiment_allocation (id),
    document_version_id     UUID        NOT NULL REFERENCES document_version (id),
    reviewer_id             UUID        NOT NULL REFERENCES app_user (id),
    condition_code          TEXT        NOT NULL CHECK (condition_code IN ('A_MANUAL','B_RULES','C_AI_ASSISTED','H3_NO_SPAN_ABSTENTION')),
    active_seconds          INT         NOT NULL CHECK (active_seconds >= 0),
    pause_seconds           INT         NOT NULL DEFAULT 0 CHECK (pause_seconds >= 0),
    corrections_count       INT         NOT NULL DEFAULT 0 CHECK (corrections_count >= 0),
    critical_errors_count   INT         NOT NULL DEFAULT 0 CHECK (critical_errors_count >= 0),
    document_difficulty     TEXT        NOT NULL DEFAULT 'MEDIA' CHECK (document_difficulty IN ('BAIXA','MEDIA','ALTA')),
    completed_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

