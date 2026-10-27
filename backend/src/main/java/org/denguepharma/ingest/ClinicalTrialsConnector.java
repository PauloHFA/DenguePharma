package org.denguepharma.ingest;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.IOException;
import java.net.URI;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/** ClinicalTrials.gov API v2, paginada por pageToken. */
public class ClinicalTrialsConnector implements SourceConnector {

    private final String baseUrl;
    private final HttpSupport http;
    private final ObjectMapper om;
    private final int pageSize;

    public ClinicalTrialsConnector(String baseUrl, HttpSupport http, ObjectMapper om, int pageSize) {
        this.baseUrl = baseUrl;
        this.http = http;
        this.om = om;
        this.pageSize = pageSize;
    }

    @Override
    public String source() {
        return "CLINICALTRIALS";
    }

    @Override
    public String connectorVersion() {
        return "ctgov-api-v2/1";
    }

    @Override
    public String describeQuery(JsonNode strategy, LocalDate cutoff) {
        return "query.cond=" + strategy.path("clinicaltrials").path("condition").asText()
                + " [LastUpdatePostDate <= " + cutoff + "]";
    }

    @Override
    public Page fetch(JsonNode strategy, LocalDate cutoff, JsonNode checkpoint) throws IOException, InterruptedException {
        Map<String, Object> params = new LinkedHashMap<>();
        params.put("query.cond", strategy.path("clinicaltrials").path("condition").asText());
        params.put("filter.advanced", "AREA[LastUpdatePostDate]RANGE[MIN," + cutoff + "]");
        params.put("pageSize", pageSize);
        params.put("countTotal", "true");
        params.put("format", "json");
        String token = checkpoint == null ? null : checkpoint.path("pageToken").asText(null);
        if (token != null) params.put("pageToken", token);

        String qs = params.entrySet().stream()
                .map(e -> URLEncoder.encode(e.getKey(), StandardCharsets.UTF_8) + "="
                        + URLEncoder.encode(String.valueOf(e.getValue()), StandardCharsets.UTF_8))
                .collect(Collectors.joining("&"));
        JsonNode body = om.readTree(http.get(URI.create(baseUrl + "/studies?" + qs)));

        List<RawRecord> records = new ArrayList<>();
        for (JsonNode study : body.path("studies")) {
            String nct = study.path("protocolSection").path("identificationModule").path("nctId").asText(null);
            if (nct == null || nct.isBlank()) continue;
            ObjectNode payload = (ObjectNode) study.deepCopy();
            // versionHolder muda a cada atualização do cache da API sem que o estudo mude: não é conteúdo.
            JsonNode misc = payload.path("derivedSection").path("miscInfoModule");
            if (misc instanceof ObjectNode m) m.remove("versionHolder");
            String title = study.path("protocolSection").path("identificationModule").path("briefTitle").asText(null);
            records.add(new RawRecord("CLINICALTRIALS", "NCT", nct, "REGISTRO_ENSAIO", title, payload,
                    "TEXTO_COMPLETO", List.of()));
        }

        String next = body.path("nextPageToken").asText(null);
        JsonNode nextCheckpoint = (next == null || next.isBlank()) ? null : om.createObjectNode().put("pageToken", next);
        Integer total = body.has("totalCount") ? body.path("totalCount").asInt() : null;
        return new Page(records, nextCheckpoint, total, "v2", params);
    }
}

