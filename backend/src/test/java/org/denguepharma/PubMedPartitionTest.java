package org.denguepharma;

import static org.assertj.core.api.Assertions.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpServer;
import java.net.*;
import java.net.http.HttpClient;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.util.*;
import org.denguepharma.ingest.*;
import org.junit.jupiter.api.Test;

class PubMedPartitionTest {
    @Test void buscaGrandeDividePeriodosEPreservaCheckpoint() throws Exception {
        var mapper=new ObjectMapper();
        var requests=new ArrayList<Map<String,String>>();
        var server=HttpServer.create(new InetSocketAddress("127.0.0.1",0),0);
        server.createContext("/esearch.fcgi",exchange->{
            Map<String,String> query=new HashMap<>();
            for(String part:exchange.getRequestURI().getRawQuery().split("&")) {
                var pieces=part.split("=",2); query.put(pieces[0],URLDecoder.decode(pieces[1],StandardCharsets.UTF_8));
            }
            requests.add(query);
            boolean whole=query.get("mindate").equals("1800/01/01") && query.get("maxdate").equals("2026/10/27");
            String response=whole?"{\"esearchresult\":{\"count\":\"10000\",\"idlist\":[]}}":"{\"esearchresult\":{\"count\":\"5000\",\"idlist\":[\"1\",\"2\"]}}";
            byte[] bytes=response.getBytes(StandardCharsets.UTF_8);exchange.sendResponseHeaders(200,bytes.length);exchange.getResponseBody().write(bytes);exchange.close();
        });
        server.createContext("/efetch.fcgi",exchange->{
            byte[] bytes="<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>1</PMID><Article><ArticleTitle>A</ArticleTitle></Article></MedlineCitation></PubmedArticle><PubmedArticle><MedlineCitation><PMID>2</PMID><Article><ArticleTitle>B</ArticleTitle></Article></MedlineCitation></PubmedArticle></PubmedArticleSet>".getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(200,bytes.length);exchange.getResponseBody().write(bytes);exchange.close();
        });
        server.start();
        try {
            var connector=new PubMedConnector("http://127.0.0.1:"+server.getAddress().getPort(),new HttpSupport(HttpClient.newHttpClient(),"test",0,1,0,millis->{}),mapper,2,null,null);
            var strategy=mapper.readTree("{\"pubmed\":{\"query\":\"dengue\"}}");
            var first=connector.fetch(strategy,LocalDate.of(2026,10,27),null);
            assertThat(first.total()).isEqualTo(10000);
            assertThat(first.nextCheckpoint().path("retstart").asInt()).isEqualTo(2);
            assertThat(first.nextCheckpoint().path("pending").size()).isOne();
            var second=connector.fetch(strategy,LocalDate.of(2026,10,27),first.nextCheckpoint());
            assertThat(second.nextCheckpoint().path("retstart").asInt()).isEqualTo(4);
            assertThat(requests.get(1).get("maxdate")).isEqualTo(requests.get(2).get("maxdate"));
            assertThat(requests.get(2).get("retstart")).isEqualTo("2");
        } finally { server.stop(0); }
    }
}
