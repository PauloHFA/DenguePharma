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
import java.util.List;
import java.util.Map;

/**
 * Conector PMC Open Access / Europe PMC REST API (Seção 7 e RNF-03).
 * Recupera metadados e licença explícita por artigo (ex.: CC-BY, CC0) para controle de redistribuição.
 */
public class EuropePmcConnector implements SourceConnector {

    private final String sourceName;
    private final String baseUrl;
    private final HttpSupport http;
    private final ObjectMapper om;
    private final int pageSize;

    public EuropePmcConnector(String sourceName, String baseUrl, HttpSupport http, ObjectMapper om, int pageSize) {
        this.sourceName = sourceName;
        this.baseUrl = baseUrl.replaceAll("/+$", "");
        this.http = http;
        this.om = om;
        this.pageSize = pageSize;
    }

    @Override
    public String source() {
        return sourceName;
    }

    @Override
    public String connectorVersion() {
        return "europepmc-rest/1.0";
    }

    @Override
    public String describeQuery(JsonNode strategy, LocalDate cutoff) {
        JsonNode node = strategy.path(sourceName);
        String q = node.isTextual() ? node.asText() : node.path("query").asText("(dengue) AND (OPEN_ACCESS:y)");
        return q + " AND (FIRST_PDATE:[1900-01-01 TO " + cutoff + "])";
    }

    @Override
    public Page fetch(JsonNode strategy, LocalDate cutoff, JsonNode checkpoint) throws IOException, InterruptedException {
        String cursorMark = checkpoint != null && checkpoint.hasNonNull("cursorMark")
                ? checkpoint.get("cursorMark").asText()
                : "*";
        String fullQuery = describeQuery(strategy, cutoff);
        String url = baseUrl + "/search?query=" + URLEncoder.encode(fullQuery, StandardCharsets.UTF_8)
                + "&resultType=core&format=json&pageSize=" + pageSize
                + "&cursorMark=" + URLEncoder.encode(cursorMark, StandardCharsets.UTF_8);

        String body = http.get(URI.create(url));
        JsonNode root = om.readTree(body);
        int hitCount = root.path("hitCount").asInt(0);
        String nextCursor = root.path("nextCursorMark").asText(null);
        JsonNode results = root.path("resultList").path("result");

        List<RawRecord> out = new ArrayList<>();
        if (results.isArray()) {
            for (JsonNode r : results) {
                String pmcid = r.path("pmcid").asText(null);
                String pmid = r.path("pmid").asText(null);
                String extId = pmcid != null && !pmcid.isBlank() ? pmcid : (pmid != null ? pmid : r.path("id").asText());
                if (extId == null || extId.isBlank()) continue;

                String title = r.path("title").asText("Sem título");
                String isOa = r.path("isOpenAccess").asText("N");
                String license = r.path("license").asText("");
                String accessStatus = "Y".equalsIgnoreCase(isOa) ? "TEXTO_COMPLETO" : "SOMENTE_RESUMO";

                ObjectNode payload = om.createObjectNode();
                payload.put("pmcid", pmcid);
                payload.put("pmid", pmid);
                payload.put("doi", r.path("doi").asText(null));
                payload.put("title", title);
                payload.put("abstract", r.path("abstractText").asText(""));
                payload.put("license", license.isBlank() ? ("Y".equalsIgnoreCase(isOa) ? "CC-BY" : "RESTRITA") : license.toUpperCase());
                payload.put("journal", r.path("journalTitle").asText(""));
                payload.put("pubYear", r.path("pubYear").asText(""));

                List<Identifier> secondary = new ArrayList<>();
                if (pmid != null && !pmid.isBlank()) {
                    secondary.add(new Identifier("PUBMED", "PMID", pmid));
                }
                String doi = r.path("doi").asText(null);
                if (doi != null && !doi.isBlank()) {
                    secondary.add(new Identifier("CROSSREF", "DOI", doi.toLowerCase()));
                }

                out.add(new RawRecord(sourceName, pmcid != null ? "PMCID" : "OUTRO", extId,
                        "PUBLICACAO", title, payload, accessStatus, secondary));
            }
        }

        JsonNode nextCp = null;
        if (nextCursor != null && !nextCursor.equals(cursorMark) && results.size() >= pageSize) {
            ObjectNode cp = om.createObjectNode();
            cp.put("cursorMark", nextCursor);
            nextCp = cp;
        }
        return new Page(out, nextCp, hitCount, root.path("version").asText("6.9"),
                Map.of("query", fullQuery, "cursorMark", cursorMark, "pageSize", pageSize));
    }
}

