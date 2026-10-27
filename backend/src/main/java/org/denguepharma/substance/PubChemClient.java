package org.denguepharma.substance;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.net.URI;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import org.denguepharma.ingest.HttpSupport;

/**
 * Conector PubChem PUG REST (Seção 05, RF-03).
 * Normaliza entidade química (CID, nome IUPAC/título e sinônimos) sem inferir aprovação ou eficácia (RC-02).
 */
public class PubChemClient {

    public record PubChemEntry(String cid, String normalizedName, String iupacName, List<String> synonyms) {}

    private final String baseUrl;
    private final HttpSupport http;
    private final ObjectMapper om;

    public PubChemClient(String baseUrl, HttpSupport http, ObjectMapper om) {
        this.baseUrl = baseUrl;
        this.http = http;
        this.om = om;
    }

    public Optional<PubChemEntry> lookupByName(String name) throws IOException, InterruptedException {
        String encoded = URLEncoder.encode(name.trim(), StandardCharsets.UTF_8).replace("+", "%20");
        URI propUri = URI.create(baseUrl + "/compound/name/" + encoded + "/property/Title,IUPACName/JSON");
        String propBody;
        try {
            propBody = http.get(propUri);
        } catch (IOException e) {
            if (e.getMessage() != null && e.getMessage().startsWith("HTTP 404")) {
                return Optional.empty();
            }
            throw e;
        }
        JsonNode props = om.readTree(propBody).path("PropertyTable").path("Properties");
        if (!props.isArray() || props.isEmpty()) {
            return Optional.empty();
        }
        JsonNode first = props.get(0);
        String cid = first.path("CID").asText(null);
        if (cid == null || cid.isBlank()) {
            return Optional.empty();
        }
        String title = first.path("Title").asText(name.trim());
        String iupac = first.path("IUPACName").asText(null);

        List<String> synonyms = new ArrayList<>();
        try {
            URI synUri = URI.create(baseUrl + "/compound/cid/" + cid + "/synonyms/JSON");
            JsonNode synList = om.readTree(http.get(synUri))
                    .path("InformationList").path("Information");
            if (synList.isArray() && !synList.isEmpty()) {
                for (JsonNode s : synList.get(0).path("Synonym")) {
                    if (synonyms.size() >= 20) break;
                    synonyms.add(s.asText());
                }
            }
        } catch (IOException ignored) {
            // Sinônimos são complementares; falha não invalida o CID obtido.
        }
        return Optional.of(new PubChemEntry(cid, title, iupac, synonyms));
    }
}
