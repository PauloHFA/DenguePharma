package org.denguepharma.ingest;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.IOException;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;

/** Fonte de registros. Cada chamada busca uma página a partir do checkpoint (nulo = início). */
public interface SourceConnector {

    String source();

    String connectorVersion();

    /** Texto da estratégia efetivamente usada, para arquivar em search_run.query. */
    String describeQuery(JsonNode strategy, LocalDate cutoff);

    Page fetch(JsonNode strategy, LocalDate cutoff, JsonNode checkpoint) throws IOException, InterruptedException;

    /** Identificador externo adicional ligado ao mesmo estudo (DOI, PMCID). */
    record Identifier(String source, String idType, String value) {}

    /** Registro bruto normalizado. {@code payload} é o conteúdo versionado e hasheado. */
    record RawRecord(String source, String idType, String externalId, String docType, String title,
                     ObjectNode payload, String accessStatus, List<Identifier> secondary) {}

    /**
     * @param nextCheckpoint nulo quando não há mais páginas
     * @param total          total informado pela fonte, quando houver
     * @param params         parâmetros exatos desta página (arquivados no protocolo de busca)
     */
    record Page(List<RawRecord> records, JsonNode nextCheckpoint, Integer total, String apiVersion,
                Map<String, Object> params) {}
}

