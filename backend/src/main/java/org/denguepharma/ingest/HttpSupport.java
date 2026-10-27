package org.denguepharma.ingest;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Cliente HTTP com respeito a quotas (RNF-05): intervalo mínimo entre chamadas, Retry-After
 * e backoff exponencial com jitter. Falha de forma explícita depois do limite de tentativas.
 */
public class HttpSupport {

    public interface Sleeper {
        void sleep(long millis) throws InterruptedException;
    }

    public static class SourceUnavailableException extends IOException {
        public SourceUnavailableException(String message, Throwable cause) {
            super(message, cause);
        }
    }

    private final HttpClient client;
    private final String userAgent;
    private final long minIntervalMs;
    private final int maxAttempts;
    private final long baseBackoffMs;
    private final Sleeper sleeper;
    private long lastCallAt = 0;

    public HttpSupport(HttpClient client, String userAgent, long minIntervalMs, int maxAttempts,
                       long baseBackoffMs, Sleeper sleeper) {
        this.client = client;
        this.userAgent = userAgent;
        this.minIntervalMs = minIntervalMs;
        this.maxAttempts = maxAttempts;
        this.baseBackoffMs = baseBackoffMs;
        this.sleeper = sleeper;
    }

    public static HttpSupport standard(String userAgent, long minIntervalMs) {
        HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(15)).build();
        return new HttpSupport(client, userAgent, minIntervalMs, 5, 1000, Thread::sleep);
    }

    public String get(URI uri) throws IOException, InterruptedException {
        String lastProblem = "";
        for (int attempt = 1; attempt <= maxAttempts; attempt++) {
            throttle();
            long waitMs = backoff(attempt);
            try {
                HttpRequest req = HttpRequest.newBuilder(uri).timeout(Duration.ofSeconds(60))
                        .header("User-Agent", userAgent).header("Accept", "application/json, application/xml").GET().build();
                HttpResponse<String> res = client.send(req, HttpResponse.BodyHandlers.ofString());
                int code = res.statusCode();
                if (code >= 200 && code < 300) {
                    return res.body();
                }
                if (code == 429 || code >= 500) {
                    lastProblem = "HTTP " + code;
                    waitMs = res.headers().firstValue("Retry-After").map(HttpSupport::parseSeconds)
                            .map(s -> s * 1000).orElse(waitMs);
                } else {
                    // Erro do cliente (4xx): repetir não ajuda.
                    throw new IOException("HTTP " + code + " em " + uri.getPath());
                }
            } catch (IOException e) {
                if (e instanceof SourceUnavailableException || e.getMessage() != null && e.getMessage().startsWith("HTTP 4")) {
                    throw e;
                }
                lastProblem = e.getClass().getSimpleName() + ": " + e.getMessage();
            }
            if (attempt < maxAttempts) {
                sleeper.sleep(waitMs);
            }
        }
        throw new SourceUnavailableException(
                "fonte indisponivel apos " + maxAttempts + " tentativas (" + lastProblem + ") em " + uri.getPath(), null);
    }

    private synchronized void throttle() throws InterruptedException {
        long now = System.currentTimeMillis();
        long wait = lastCallAt + minIntervalMs - now;
        if (wait > 0) {
            sleeper.sleep(wait);
        }
        lastCallAt = System.currentTimeMillis();
    }

    private long backoff(int attempt) {
        long exp = baseBackoffMs * (1L << Math.min(attempt - 1, 6));
        return exp + ThreadLocalRandom.current().nextLong(0, Math.max(1, baseBackoffMs));
    }

    private static Long parseSeconds(String v) {
        try {
            return Math.max(0, Long.parseLong(v.trim()));
        } catch (NumberFormatException e) {
            return null; // Retry-After em formato de data não é usado pelas fontes; cai no backoff.
        }
    }
}

