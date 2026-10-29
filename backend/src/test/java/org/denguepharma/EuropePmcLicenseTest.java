package org.denguepharma;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.net.http.HttpClient;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import org.denguepharma.ingest.EuropePmcConnector;
import org.denguepharma.ingest.HttpSupport;
import org.junit.jupiter.api.Test;

class EuropePmcLicenseTest {
    @Test
    void acessoAbertoSemLicencaNaoAutorizaRedistribuicao() throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/search", exchange -> {
            byte[] body = """
                    {"hitCount":2,"resultList":{"result":[
                    {"pmcid":"PMC1","title":"Sem licenca","isOpenAccess":"Y"},
                    {"pmcid":"PMC2","title":"Licenca explicita","isOpenAccess":"Y","license":"CC-BY"}]}}
                    """.getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(200, body.length);
            exchange.getResponseBody().write(body);
            exchange.close();
        });
        server.start();
        try {
            ObjectMapper mapper = new ObjectMapper();
            HttpSupport http = new HttpSupport(HttpClient.newHttpClient(), "test", 0, 1, 1, ms -> {});
            EuropePmcConnector connector = new EuropePmcConnector("EUROPE_PMC",
                    "http://127.0.0.1:" + server.getAddress().getPort(), http, mapper, 100);
            var records = connector.fetch(mapper.createObjectNode(), LocalDate.of(2026, 10, 26), null).records();
            assertThat(records.get(0).payload().path("license").asText()).isEqualTo("NAO_VERIFICADA");
            assertThat(records.get(1).payload().path("license").asText()).isEqualTo("CC-BY");
        } finally {
            server.stop(0);
        }
    }
}
