package org.denguepharma;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.URLDecoder;
import java.net.http.HttpClient;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import org.denguepharma.audit.AuditService;
import org.denguepharma.ingest.ClinicalTrialsConnector;
import org.denguepharma.ingest.HttpSupport;
import org.denguepharma.ingest.ImportService;
import org.denguepharma.ingest.PubMedConnector;
import org.denguepharma.ingest.SourceConnector;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.web.server.ResponseStatusException;

/** RF-02 com servidores HTTP falsos: nenhuma chamada de rede real. */
class ImportIntegrationTest extends AbstractIntegrationTest {

    @Autowired PlatformTransactionManager tm;
    @Autowired AuditService audit;

    HttpServer server;
    String baseUrl;
    final List<Long> sleeps = Collections.synchronizedList(new ArrayList<>());

    // estado mutável dos servidores falsos
    final Map<String, String> abstracts = new HashMap<>();   // pmid -> resumo
    final Map<String, String> dois = new HashMap<>();        // pmid -> doi
    List<String> pmids = List.of("111", "222", "333");
    final AtomicBoolean failCtPage2 = new AtomicBoolean(false);
    final AtomicInteger throttledOnce = new AtomicInteger(0);
    boolean throttleFirstEsearch = false;

    ImportService service;
    UUID protocolId;

    @BeforeEach
    void setUp() throws Exception {
        abstracts.clear();
        dois.clear();
        pmids = List.of("111", "222", "333");
        for (String id : List.of("111", "222", "333", "444")) {
            abstracts.put(id, "resumo " + id);
            dois.put(id, "10.1/" + id);
        }
        failCtPage2.set(false);
        throttledOnce.set(0);
        throttleFirstEsearch = false;
        sleeps.clear();

        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/entrez/eutils/esearch.fcgi", this::esearch);
        server.createContext("/entrez/eutils/efetch.fcgi", this::efetch);
        server.createContext("/ct/studies", this::ctStudies);
        server.start();
        baseUrl = "http://127.0.0.1:" + server.getAddress().getPort();

        HttpSupport http = new HttpSupport(HttpClient.newHttpClient(), "teste", 0, 2, 10, sleeps::add);
        List<SourceConnector> connectors = List.of(
                new PubMedConnector(baseUrl + "/entrez/eutils", http, json, 2, null, null),
                new ClinicalTrialsConnector(baseUrl + "/ct", http, json, 2));
        service = new ImportService(jdbc, tm, json, audit, connectors);
        protocolId = registeredProtocol();
    }

    @AfterEach
    void tearDown() {
        server.stop(0);
    }

    // ---------- testes ----------

    @Test
    void T1_reimportarOMesmoRegistroNaoDuplicaEstudo() {
        UUID first = run("PUBMED");
        assertThat(counts(first)).containsExactly(3, 3, 0, 0);

        UUID second = run("PUBMED");
        assertThat(counts(second)).containsExactly(3, 0, 0, 3);

        assertThat(count("select count(*) from study")).isEqualTo(3);
        assertThat(count("select count(*) from document_version")).isEqualTo(3);
        assertThat(count("select count(*) from study_identifier where id_type = 'PMID'")).isEqualTo(3);
    }

    @Test
    void T2_novaVersaoDaFonteNaoSobrescreveAnterior() {
        run("PUBMED");
        String hashV1 = jdbc.queryForObject("""
                select dv.content_hash from document_version dv join study_document sd on sd.document_id = dv.document_id
                join study_identifier si on si.study_id = sd.study_id
                where si.value = '222' and si.id_type = 'PMID' and dv.version_no = 1""", String.class);

        abstracts.put("222", "resumo 222 CORRIGIDO");
        UUID second = run("PUBMED");
        assertThat(counts(second)).containsExactly(3, 0, 1, 2);

        List<Integer> versions = jdbc.queryForList("""
                select dv.version_no from document_version dv join study_document sd on sd.document_id = dv.document_id
                join study_identifier si on si.study_id = sd.study_id
                where si.value = '222' and si.id_type = 'PMID' order by 1""", Integer.class);
        assertThat(versions).containsExactly(1, 2);
        assertThat(count("select count(*) from document_version where content_hash = '" + hashV1 + "'")).isEqualTo(1);
        assertThat(count("select count(*) from outbox where event_type = 'FonteAlterada'")).isEqualTo(1);
        assertThat(count("select count(*) from study")).isEqualTo(3);
    }

    @Test
    void eventoDeImportacaoUsaApenasReferencias() {
        run("PUBMED");
        assertThat(count("select count(*) from outbox where event_type = 'DocumentoImportado'")).isEqualTo(3);
        String payload = jdbc.queryForObject("select payload::text from outbox limit 1", String.class);
        assertThat(payload).contains("document_version_id").contains("content_hash").doesNotContain("resumo");
    }

    @Test
    void checkpointPermiteRetomarAposFalhaSemDuplicar() {
        failCtPage2.set(true);
        UUID id = run("CLINICALTRIALS");

        assertThat(status(id)).isEqualTo("FAILED");
        assertThat(jdbc.queryForObject("select checkpoint->>'pageToken' from search_run where id = ?", String.class, id))
                .isEqualTo("p2");
        assertThat(count("select count(*) from study")).isEqualTo(2);   // página 1 já persistida

        failCtPage2.set(false);
        service.resumeMarker(id);
        service.execute(id);

        assertThat(status(id)).isEqualTo("COMPLETED");
        assertThat(counts(id)).containsExactly(3, 3, 0, 0);
        assertThat(count("select count(*) from study")).isEqualTo(3);
        assertThat(count("select count(*) from study_identifier where id_type = 'NCT'")).isEqualTo(3);
        assertThat(jdbc.queryForObject("select checkpoint from search_run where id = ?", String.class, id)).isNull();
    }

    @Test
    void respeitaRetryAfterEmCasoDeLimiteDeTaxa() {
        throttleFirstEsearch = true;
        UUID id = run("PUBMED");
        assertThat(status(id)).isEqualTo("COMPLETED");
        assertThat(sleeps).contains(2000L);   // Retry-After: 2
    }

    @Test
    void parametrosExatosFicamArquivados() {
        UUID id = run("PUBMED");
        String params = jdbc.queryForObject("select params::text from search_run where id = ?", String.class, id);
        assertThat(params).contains("\"maxdate\": \"2026/10/26\"").contains("\"db\": \"pubmed\"");
        assertThat(jdbc.queryForObject("select pagination->'pages'->0->>'returned' from search_run where id = ?",
                String.class, id)).isEqualTo("2");
        assertThat(jdbc.queryForObject("select total_returned from search_run where id = ?", Integer.class, id)).isEqualTo(3);
    }

    @Test
    void T3_mesmoDoiEmEstudosDiferentesNaoFundeAutomaticamente() {
        dois.put("333", "10.1/111");   // 333 reivindica o DOI do 111
        run("PUBMED");

        assertThat(count("select count(*) from study")).isEqualTo(3);
        assertThat(count("select count(*) from audit_log where action = 'IDENTIFIER_CONFLICT'")).isEqualTo(1);
    }

    @Test
    void naoImportaComProtocoloEmRascunho() {
        UUID draft = UUID.randomUUID();
        jdbc.update("""
                insert into protocol (id, code, version, title, question, sources, strategy, eligibility, cutoff_date)
                values (?, 'RASC', 1, 't', 'q', '["PUBMED"]', '{"pubmed":{"query":"dengue"}}', '{"a":"b"}', '2026-10-26')
                """, draft);
        assertThatThrownBy(() -> service.start(draft, "PUBMED", null)).isInstanceOf(ResponseStatusException.class);
    }

    @Test
    void xmlComDoctypeExternoNaoBuscaDtd() {
        // O XML do teste declara DTD externo inacessível; a leitura não pode tentar baixá-lo.
        UUID id = run("PUBMED");
        assertThat(status(id)).isEqualTo("COMPLETED");
    }

    // ---------- helpers ----------

    UUID run(String source) {
        UUID id = service.start(protocolId, source, null);
        service.execute(id);
        return id;
    }

    String status(UUID id) {
        return jdbc.queryForObject("select status from search_run where id = ?", String.class, id);
    }

    List<Integer> counts(UUID id) {
        return jdbc.query("select records_seen, records_created, records_updated, records_unchanged from search_run where id = ?",
                (rs, i) -> Arrays.asList(rs.getInt(1), rs.getInt(2), rs.getInt(3), rs.getInt(4)), id).get(0);
    }

    int count(String sql) {
        return jdbc.queryForObject(sql, Integer.class);
    }

    UUID registeredProtocol() {
        UUID id = UUID.randomUUID();
        jdbc.update("""
                insert into protocol (id, code, version, title, question, sources, strategy, eligibility, cutoff_date)
                values (?, 'P', 1, 't', 'q', '["PUBMED","CLINICALTRIALS"]',
                        '{"pubmed":{"query":"dengue"},"clinicaltrials":{"condition":"dengue"}}', '{"a":"b"}', ?)
                """, id, LocalDate.of(2026, 10, 26));
        jdbc.update("update protocol set status = 'REGISTERED' where id = ?", id);
        return id;
    }

    // ---------- servidores falsos ----------

    Map<String, String> query(HttpExchange ex) {
        Map<String, String> q = new HashMap<>();
        String raw = ex.getRequestURI().getRawQuery();
        if (raw != null) {
            for (String kv : raw.split("&")) {
                String[] p = kv.split("=", 2);
                q.put(URLDecoder.decode(p[0], StandardCharsets.UTF_8), p.length > 1 ? URLDecoder.decode(p[1], StandardCharsets.UTF_8) : "");
            }
        }
        return q;
    }

    void respond(HttpExchange ex, int code, String body, Map<String, String> headers) throws IOException {
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        headers.forEach((k, v) -> ex.getResponseHeaders().add(k, v));
        ex.sendResponseHeaders(code, bytes.length == 0 ? -1 : bytes.length);
        if (bytes.length > 0) ex.getResponseBody().write(bytes);
        ex.close();
    }

    void esearch(HttpExchange ex) throws IOException {
        if (throttleFirstEsearch && throttledOnce.getAndIncrement() == 0) {
            respond(ex, 429, "slow down", Map.of("Retry-After", "2"));
            return;
        }
        Map<String, String> q = query(ex);
        int start = Integer.parseInt(q.getOrDefault("retstart", "0"));
        int max = Integer.parseInt(q.getOrDefault("retmax", "2"));
        List<String> page = pmids.subList(Math.min(start, pmids.size()), Math.min(start + max, pmids.size()));
        String ids = String.join(",", page.stream().map(s -> "\"" + s + "\"").toList());
        respond(ex, 200, "{\"esearchresult\":{\"count\":\"" + pmids.size() + "\",\"retmax\":\"" + max
                + "\",\"retstart\":\"" + start + "\",\"idlist\":[" + ids + "]}}", Map.of("Content-Type", "application/json"));
    }

    void efetch(HttpExchange ex) throws IOException {
        StringBuilder xml = new StringBuilder("""
                <?xml version="1.0" encoding="UTF-8"?>
                <!DOCTYPE PubmedArticleSet PUBLIC "-//NLM//DTD PubMedArticle, 1st January 2023//EN" "http://127.0.0.1:1/inexistente.dtd">
                <PubmedArticleSet>
                """);
        for (String id : query(ex).get("id").split(",")) {
            xml.append("<PubmedArticle><MedlineCitation><PMID Version=\"1\">").append(id).append("</PMID><Article>")
                    .append("<Journal><Title>J</Title><JournalIssue><PubDate><Year>2020</Year></PubDate></JournalIssue></Journal>")
                    .append("<ArticleTitle>Titulo ").append(id).append("</ArticleTitle>")
                    .append("<Abstract><AbstractText Label=\"BACKGROUND\">").append(abstracts.get(id)).append("</AbstractText></Abstract>")
                    .append("<Language>eng</Language><PublicationTypeList><PublicationType>Randomized Controlled Trial</PublicationType></PublicationTypeList>")
                    .append("</Article></MedlineCitation><PubmedData><ArticleIdList><ArticleId IdType=\"pubmed\">").append(id)
                    .append("</ArticleId><ArticleId IdType=\"doi\">").append(dois.get(id)).append("</ArticleId></ArticleIdList></PubmedData></PubmedArticle>");
        }
        xml.append("</PubmedArticleSet>");
        respond(ex, 200, xml.toString(), Map.of("Content-Type", "application/xml"));
    }

    void ctStudies(HttpExchange ex) throws IOException {
        String token = query(ex).get("pageToken");
        if (token == null) {
            respond(ex, 200, ctPage(List.of("NCT001", "NCT002"), "p2"), Map.of("Content-Type", "application/json"));
        } else if (failCtPage2.get()) {
            respond(ex, 500, "erro", Map.of());
        } else {
            respond(ex, 200, ctPage(List.of("NCT003"), null), Map.of("Content-Type", "application/json"));
        }
    }

    String ctPage(List<String> ncts, String next) {
        String studies = String.join(",", ncts.stream().map(n -> "{\"protocolSection\":{\"identificationModule\":{\"nctId\":\"" + n
                + "\",\"briefTitle\":\"Ensaio " + n + "\"}},\"derivedSection\":{\"miscInfoModule\":{\"versionHolder\":\""
                + System.nanoTime() + "\"}}}").toList());
        return "{\"studies\":[" + studies + "],\"totalCount\":3" + (next == null ? "" : ",\"nextPageToken\":\"" + next + "\"") + "}";
    }
}

