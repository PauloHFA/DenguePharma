package org.denguepharma.analysis;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.denguepharma.catalog.CatalogService.CatalogFilter;
import org.springframework.http.*;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/analyses")
public class AnalysisController {
    private final AnalysisService service;
    private final CorpusService corpus;
    private final org.springframework.jdbc.core.JdbcTemplate jdbc;
    public AnalysisController(AnalysisService service, CorpusService corpus, org.springframework.jdbc.core.JdbcTemplate jdbc) { this.service=service; this.corpus=corpus; this.jdbc=jdbc; }
    @PostMapping
    @ResponseStatus(HttpStatus.ACCEPTED)
    @PreAuthorize("hasAnyRole('PESQUISADOR','ADMINISTRADOR')")
    public Map<String,Object> create(@RequestBody(required=false) CatalogFilter filters, @AuthenticationPrincipal Jwt jwt) {
        return service.create(filters == null ? new CatalogFilter(null,null,null,null,null,null) : filters, UUID.fromString(jwt.getSubject()));
    }
    @PostMapping("/corpus")
    @ResponseStatus(HttpStatus.ACCEPTED)
    @PreAuthorize("hasAnyRole('PESQUISADOR','ADMINISTRADOR')")
    public Map<String,Object> corpus(@RequestBody CorpusService.Request request, @AuthenticationPrincipal Jwt jwt) {
        return corpus.create(request, UUID.fromString(jwt.getSubject()));
    }
    @PostMapping("/{id}/publish")
    @PreAuthorize("hasAnyRole('PESQUISADOR','ADMINISTRADOR')")
    @org.springframework.transaction.annotation.Transactional
    public Map<String,Object> publish(@PathVariable UUID id, @AuthenticationPrincipal Jwt jwt) {
        var input=service.input(id);
        try {
            var node=new com.fasterxml.jackson.databind.ObjectMapper().readTree((String)input.get("content"));
            if(!"3.0".equals(node.path("schemaVersion").asText())) throw new org.springframework.web.server.ResponseStatusException(HttpStatus.CONFLICT,"somente corpus v3 pode ser publicado");
        } catch(java.io.IOException e) { throw new IllegalStateException(e); }
        if(!"COMPLETED".equals(service.get(id).get("status"))) throw new org.springframework.web.server.ResponseStatusException(HttpStatus.CONFLICT,"aguarde a conclusao da analise");
        jdbc.update("insert into analysis_publication(analysis_id,published_by) values(?,?) on conflict do nothing",id,UUID.fromString(jwt.getSubject()));
        return Map.of("id",id,"published",true);
    }
    @GetMapping public List<Map<String,Object>> list() { return service.list(); }
    @GetMapping("/{id}") public Map<String,Object> get(@PathVariable UUID id) { return service.get(id); }
    @GetMapping("/{id}/artifacts")
    public ResponseEntity<byte[]> artifact(@PathVariable UUID id, @RequestParam String name) {
        var file=service.artifact(id,name);
        return ResponseEntity.ok().contentType(MediaType.parseMediaType(file.mediaType()))
                .header(HttpHeaders.CONTENT_DISPOSITION, ContentDisposition.attachment().filename(name.substring(name.lastIndexOf('/')+1)).build().toString())
                .body(file.content());
    }
}
