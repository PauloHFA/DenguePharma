package org.denguepharma.pipeline;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.denguepharma.extraction.ExtractionController.SubmitRunRequest;
import org.denguepharma.extraction.ExtractionService.RunInput;
import org.denguepharma.pipeline.PipelineService.Artifact;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/internal/pipeline")
public class PipelineController {
    public record Lease(@NotNull UUID leaseToken) {}
    public record Delivery(@NotNull UUID eventId) {}
    public record Archive(@NotNull UUID leaseToken, @NotNull String contentHash, long sizeBytes) {}
    public record Failure(@NotNull UUID leaseToken, String errorCode) {}
    public record Extraction(@NotNull UUID leaseToken, @Valid @NotNull SubmitRunRequest extraction) {}
    public record Report(@NotNull UUID leaseToken, @NotNull List<@NotNull Artifact> artifacts) {}
    public record Analysis(@NotNull UUID leaseToken, @NotNull @Size(max=44739244) String bundleBase64) {}
    private final PipelineService service;
    public PipelineController(PipelineService service) { this.service = service; }

    @PostMapping("/outbox/claim")
    public List<Map<String, Object>> outbox(@RequestParam(defaultValue = "20") int limit) { return service.claimOutbox(limit); }
    @PostMapping("/outbox/{event}/confirm")
    public void confirm(@PathVariable UUID event, @Valid @RequestBody Lease lease) { service.confirmOutbox(event, lease.leaseToken()); }
    @PostMapping("/outbox/{event}/fail")
    public void failPublication(@PathVariable UUID event, @Valid @RequestBody Lease lease) { service.failOutbox(event, lease.leaseToken()); }
    @PostMapping("/deliveries/claim")
    public Map<String, Object> delivery(@Valid @RequestBody Delivery input) { return service.claimDelivery(input.eventId()); }
    @PostMapping("/jobs/{job}/renew")
    public void renew(@PathVariable UUID job, @Valid @RequestBody Lease lease) { service.renew(job, lease.leaseToken()); }
    @GetMapping("/jobs/{job}/input")
    public Map<String, Object> input(@PathVariable UUID job, @RequestHeader("X-Lease-Token") UUID lease) { return service.input(job, lease); }
    @PostMapping("/jobs/{job}/archive")
    public void archive(@PathVariable UUID job, @Valid @RequestBody Archive input) { service.archive(job, input.leaseToken(), input.contentHash(), input.sizeBytes()); }
    @PostMapping("/jobs/{job}/extraction")
    public Map<String, Object> extraction(@PathVariable UUID job, @Valid @RequestBody Extraction input) {
        var e = input.extraction();
        return service.completeExtraction(job, input.leaseToken(), new RunInput(e.documentVersionId(), e.pipelineVersion(),
                e.modelProvider(), e.modelVersion(), e.promptHash(), e.executionVariant(), e.schemaVersion(), e.fields()));
    }
    @PostMapping("/jobs/{job}/fail")
    public Map<String, Object> fail(@PathVariable UUID job, @Valid @RequestBody Failure input) { return service.fail(job, input.leaseToken(), input.errorCode()); }
    @GetMapping("/jobs/{job}/report/{format}")
    public ResponseEntity<byte[]> reportFile(@PathVariable UUID job, @PathVariable String format, @RequestHeader("X-Lease-Token") UUID token) {
        return ResponseEntity.ok().contentType(MediaType.APPLICATION_OCTET_STREAM).body(service.reportFile(job, token, format));
    }
    @PostMapping("/jobs/{job}/report")
    public void report(@PathVariable UUID job, @Valid @RequestBody Report input) { service.completeReport(job, input.leaseToken(), input.artifacts()); }
    @PostMapping("/jobs/{job}/analysis")
    public void analysis(@PathVariable UUID job, @Valid @RequestBody Analysis input) {
        byte[] bytes;
        try { bytes = java.util.Base64.getDecoder().decode(input.bundleBase64()); }
        catch (IllegalArgumentException e) { throw new org.springframework.web.server.ResponseStatusException(org.springframework.http.HttpStatus.UNPROCESSABLE_ENTITY, "pacote base64 invalido"); }
        service.completeAnalysis(job,input.leaseToken(),bytes);
    }
}
