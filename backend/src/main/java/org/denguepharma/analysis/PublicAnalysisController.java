package org.denguepharma.analysis;

import java.util.*;
import org.springframework.http.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/public/analyses")
public class PublicAnalysisController {
    private final JdbcTemplate jdbc;
    private final AnalysisService analyses;
    public PublicAnalysisController(JdbcTemplate jdbc,AnalysisService analyses) { this.jdbc=jdbc; this.analyses=analyses; }
    @GetMapping public List<Map<String,Object>> list() {
        return jdbc.queryForList("""
                select a.id,p.published_at,s.content_hash as input_hash,s.dataset->'protocol'->>'code' as protocol_code,
                    s.dataset->'protocol'->>'cutoff_date' as cutoff_date,
                    jsonb_array_length(s.dataset->'documents') as document_count,
                    jsonb_array_length(s.dataset->'studies') as study_count
                from analysis_publication p join analysis_run a on a.id=p.analysis_id
                join analysis_snapshot s on s.id=a.snapshot_id
                order by p.published_at desc,a.id limit 200
                """);
    }
    @GetMapping("/{id}") public Map<String,Object> get(@PathVariable UUID id) {
        requirePublished(id);
        return Map.of("id",id,"status","COMPLETED","artifacts",jdbc.queryForList("select name,media_type,content_hash,octet_length(content) as size_bytes from analysis_artifact where analysis_id=? order by name",id));
    }
    @GetMapping("/{id}/artifacts") public ResponseEntity<byte[]> artifact(@PathVariable UUID id,@RequestParam String name) {
        requirePublished(id);
        // Apenas artefatos validados de snapshots v3; jamais expor a API operacional.
        var file=analyses.artifact(id,name);
        return ResponseEntity.ok().contentType(MediaType.parseMediaType(file.mediaType()))
            .header(HttpHeaders.CONTENT_DISPOSITION,ContentDisposition.attachment().filename(name.substring(name.lastIndexOf('/')+1)).build().toString())
            .header("X-Content-Type-Options","nosniff").body(file.content());
    }
    private void requirePublished(UUID id) {
        if(!Boolean.TRUE.equals(jdbc.queryForObject("select exists(select 1 from analysis_publication where analysis_id=?)",Boolean.class,id)))
            throw new ResponseStatusException(HttpStatus.NOT_FOUND,"analise nao publicada");
    }
}
