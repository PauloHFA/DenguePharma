-- V2: protocolo imutável após registro (RF-01), execuções ligadas a protocolo registrado,
-- estado/checkpoint das importações (RF-02) e conteúdo estruturado das versões de documento.

-- ===== Protocolo: versão registrada não muda; mudança exige nova versão =====
CREATE FUNCTION protect_protocol() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        IF OLD.status <> 'DRAFT' THEN
            RAISE EXCEPTION 'protocolo % v% (%) nao pode ser removido', OLD.code, OLD.version, OLD.status;
        END IF;
        RETURN OLD;
    END IF;

    IF OLD.status <> 'DRAFT' AND (
        NEW.code        IS DISTINCT FROM OLD.code OR
        NEW.version     IS DISTINCT FROM OLD.version OR
        NEW.title       IS DISTINCT FROM OLD.title OR
        NEW.question    IS DISTINCT FROM OLD.question OR
        NEW.sources     IS DISTINCT FROM OLD.sources OR
        NEW.strategy    IS DISTINCT FROM OLD.strategy OR
        NEW.eligibility IS DISTINCT FROM OLD.eligibility OR
        NEW.cutoff_date IS DISTINCT FROM OLD.cutoff_date) THEN
        RAISE EXCEPTION 'protocolo % v% ja registrado: crie uma nova versao', OLD.code, OLD.version;
    END IF;

    IF NEW.status IS DISTINCT FROM OLD.status AND NOT
       ((OLD.status = 'DRAFT' AND NEW.status = 'REGISTERED') OR
        (OLD.status = 'REGISTERED' AND NEW.status = 'FROZEN')) THEN
        RAISE EXCEPTION 'transicao de status invalida: % -> %', OLD.status, NEW.status;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_protect_protocol
    BEFORE UPDATE OR DELETE ON protocol
    FOR EACH ROW EXECUTE FUNCTION protect_protocol();

-- ===== Toda execução referencia um protocolo registrado =====
CREATE FUNCTION require_registered_protocol() RETURNS trigger AS $$
DECLARE s TEXT;
BEGIN
    SELECT status INTO s FROM protocol WHERE id = NEW.protocol_id;
    IF s IS NULL OR s = 'DRAFT' THEN
        RAISE EXCEPTION 'execucao exige protocolo registrado (status atual: %)', s;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_search_run_protocol
    BEFORE INSERT ON search_run
    FOR EACH ROW EXECUTE FUNCTION require_registered_protocol();

-- ===== Estado, contadores e checkpoint da importação =====
ALTER TABLE search_run
    ADD COLUMN status          TEXT NOT NULL DEFAULT 'RUNNING'
        CHECK (status IN ('RUNNING','COMPLETED','FAILED')),
    ADD COLUMN last_error      TEXT,
    ADD COLUMN finished_at     TIMESTAMPTZ,
    ADD COLUMN requested_by    UUID REFERENCES app_user (id),
    ADD COLUMN records_seen    INT NOT NULL DEFAULT 0,
    ADD COLUMN records_created INT NOT NULL DEFAULT 0,
    ADD COLUMN records_updated INT NOT NULL DEFAULT 0,
    ADD COLUMN records_unchanged INT NOT NULL DEFAULT 0;

-- ===== Conteúdo estruturado (metadados/registro) da versão do documento =====
ALTER TABLE document_version ADD COLUMN metadata JSONB;

-- ===== Estudo recém-importado ainda não foi classificado quanto ao contexto (RC-01) =====
ALTER TABLE study DROP CONSTRAINT study_context_check;
ALTER TABLE study ADD CONSTRAINT study_context_check
    CHECK (context IN ('NAO_CLASSIFICADO','HUMANO','DESAFIO_CONTROLADO','IN_SILICO','IN_VITRO','ANIMAL'));
ALTER TABLE study ALTER COLUMN context SET DEFAULT 'NAO_CLASSIFICADO';

