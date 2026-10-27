package org.denguepharma.ingest;

import org.springframework.boot.context.properties.ConfigurationProperties;

/** Configuração das fontes. Chave e e-mail do NCBI são opcionais (a chave aumenta a quota). */
@ConfigurationProperties(prefix = "denguepharma.ingest")
public record IngestProperties(String pubmedBaseUrl, String ctgovBaseUrl, String europePmcBaseUrl,
                               String ncbiApiKey, String contactEmail,
                               int pubmedPageSize, int ctgovPageSize) {

    public IngestProperties {
        if (pubmedBaseUrl == null || pubmedBaseUrl.isBlank()) pubmedBaseUrl = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils";
        if (ctgovBaseUrl == null || ctgovBaseUrl.isBlank()) ctgovBaseUrl = "https://clinicaltrials.gov/api/v2";
        if (europePmcBaseUrl == null || europePmcBaseUrl.isBlank()) europePmcBaseUrl = "https://www.ebi.ac.uk/europepmc/webservices/rest";
        if (pubmedPageSize <= 0) pubmedPageSize = 200;
        if (ctgovPageSize <= 0) ctgovPageSize = 100;
    }

    public boolean hasApiKey() {
        return ncbiApiKey != null && !ncbiApiKey.isBlank();
    }

    public String userAgent() {
        return "DenguePharma/0.1 (pesquisa academica" + (contactEmail == null || contactEmail.isBlank() ? "" : "; " + contactEmail) + ")";
    }
}
