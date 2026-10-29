-- A semente local nao e um corpus cientifico recuperado/adjudicado.
ALTER TABLE study ADD COLUMN is_demo BOOLEAN NOT NULL DEFAULT FALSE;
UPDATE study s SET is_demo = TRUE
WHERE EXISTS (
    SELECT 1 FROM extracted_field ef
    JOIN extraction_run er ON er.id = ef.extraction_run_id
    WHERE ef.study_id = s.id AND er.prompt_hash = 'sha256-pilot-prompt'
);
