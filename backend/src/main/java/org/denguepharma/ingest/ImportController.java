package org.denguepharma.ingest;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/imports")
@PreAuthorize("hasAnyRole('PESQUISADOR','ADMINISTRADOR')")
public class ImportController {

    public record StartRequest(@NotNull UUID protocolId, @NotBlank String source) {}

    private final ImportService service;
    private final ExecutorService executor;
    private final JdbcTemplate jdbc;

    public ImportController(ImportService service, ExecutorService importExecutor, JdbcTemplate jdbc) {
        this.service = service;
        this.executor = importExecutor;
        this.jdbc = jdbc;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.ACCEPTED)
    public Map<String, Object> start(@Valid @RequestBody StartRequest req, @AuthenticationPrincipal Jwt jwt) {
        UUID runId = service.start(req.protocolId(), req.source(), UUID.fromString(jwt.getSubject()));
        executor.submit(() -> service.execute(runId));
        return Map.of("runId", runId);
    }

    @PostMapping("/{id}/resume")
    @ResponseStatus(HttpStatus.ACCEPTED)
    public Map<String, Object> resume(@PathVariable UUID id) {
        service.resumeMarker(id);
        executor.submit(() -> service.execute(id));
        return Map.of("runId", id);
    }

    @GetMapping
    public List<Map<String, Object>> list() {
        return jdbc.queryForList("""
                select sr.id, sr.protocol_id, p.code as protocol_code, p.version as protocol_version, sr.source, sr.status,
                       sr.query, sr.executed_at, sr.finished_at, sr.total_returned, sr.records_seen, sr.records_created,
                       sr.records_updated, sr.records_unchanged, sr.last_error, sr.connector_version, sr.api_version
                from search_run sr join protocol p on p.id = sr.protocol_id order by sr.executed_at desc limit 200
                """);
    }

    @GetMapping("/{id}")
    public Map<String, Object> get(@PathVariable UUID id) {
        return jdbc.queryForList("select id, protocol_id, source, status, query, params::text as params, "
                        + "pagination::text as pagination, checkpoint::text as checkpoint, last_error, executed_at, finished_at, "
                        + "total_returned, records_seen, records_created, records_updated, records_unchanged "
                        + "from search_run where id = ?", id).stream().findFirst()
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "importacao nao encontrada"));
    }
}

