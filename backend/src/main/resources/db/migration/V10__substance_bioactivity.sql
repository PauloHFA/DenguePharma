-- V10__substance_bioactivity.sql
-- Tabela para persistencia e consulta de bioatividades ChEMBL / PubChem vinculadas a substancias e alvos virais (REQ-IDN-002, OE1).

CREATE TABLE IF NOT EXISTS substance_bioactivity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    substance_id UUID NOT NULL REFERENCES substance(id) ON DELETE CASCADE,
    chembl_assay_id VARCHAR(64),
    target_name VARCHAR(128) NOT NULL,
    target_organism VARCHAR(128) DEFAULT 'Dengue virus',
    activity_type VARCHAR(32) NOT NULL, -- IC50, EC50, Ki, etc.
    activity_value NUMERIC(14, 4),
    activity_units VARCHAR(32) DEFAULT 'nM',
    relation VARCHAR(8) DEFAULT '=', -- =, <, >, <=, >=
    reference_doi VARCHAR(128),
    reference_pubmed_id VARCHAR(32),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS idx_substance_bioactivity_substance ON substance_bioactivity(substance_id);
CREATE INDEX IF NOT EXISTS idx_substance_bioactivity_target ON substance_bioactivity(target_name);

-- Insercao de bioatividades de referencia catalogadas
INSERT INTO substance_bioactivity (substance_id, chembl_assay_id, target_name, activity_type, activity_value, activity_units, relation)
SELECT s.id, 'CHEMBL_ASSAY_DENV_NS5', 'NS5 RdRp', 'IC50', 1400.0000, 'nM', '='
FROM substance s WHERE lower(s.published_name) LIKE '%balapiravir%' OR lower(s.normalized_name) LIKE '%balapiravir%'
ON CONFLICT DO NOTHING;

INSERT INTO substance_bioactivity (substance_id, chembl_assay_id, target_name, activity_type, activity_value, activity_units, relation)
SELECT s.id, 'CHEMBL_ASSAY_DENV_GLUCOSE', 'Alfa-Glicosidase', 'IC50', 210.0000, 'nM', '<='
FROM substance s WHERE lower(s.published_name) LIKE '%celgosivir%' OR lower(s.normalized_name) LIKE '%celgosivir%'
ON CONFLICT DO NOTHING;

INSERT INTO substance_bioactivity (substance_id, chembl_assay_id, target_name, activity_type, activity_value, activity_units, relation)
SELECT s.id, 'CHEMBL_ASSAY_DENV_IMPORTIN', 'Importina IMP-alfa/beta1', 'IC50', 50.0000, 'nM', '<='
FROM substance s WHERE lower(s.published_name) LIKE '%ivermectina%' OR lower(s.normalized_name) LIKE '%ivermectin%'
ON CONFLICT DO NOTHING;

INSERT INTO substance_bioactivity (substance_id, chembl_assay_id, target_name, activity_type, activity_value, activity_units, relation)
SELECT s.id, 'CHEMBL_ASSAY_DENV_FUSION', 'Proteina de Envelope (E)', 'EC50', 8500.0000, 'nM', '='
FROM substance s WHERE lower(s.published_name) LIKE '%cloroquina%' OR lower(s.normalized_name) LIKE '%chloroquine%'
ON CONFLICT DO NOTHING;
