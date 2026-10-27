package org.denguepharma.ingest;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class IngestConfig {

    // Limites públicos: E-utilities permitem 3 req/s sem chave e 10 req/s com chave.
    @Bean
    SourceConnector pubMedConnector(IngestProperties p, ObjectMapper om) {
        long interval = p.hasApiKey() ? 110 : 350;
        return new PubMedConnector(p.pubmedBaseUrl(), HttpSupport.standard(p.userAgent(), interval), om,
                p.pubmedPageSize(), p.ncbiApiKey(), p.contactEmail());
    }

    @Bean
    SourceConnector clinicalTrialsConnector(IngestProperties p, ObjectMapper om) {
        return new ClinicalTrialsConnector(p.ctgovBaseUrl(), HttpSupport.standard(p.userAgent(), 300), om,
                p.ctgovPageSize());
    }

    /** Uma importação por vez: respeita as quotas das fontes. */
    @Bean(destroyMethod = "shutdown")
    ExecutorService importExecutor() {
        return Executors.newSingleThreadExecutor(r -> {
            Thread t = new Thread(r, "import-worker");
            t.setDaemon(true);
            return t;
        });
    }
}

