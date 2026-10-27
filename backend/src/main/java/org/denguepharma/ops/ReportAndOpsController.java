package org.denguepharma.ops;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.denguepharma.catalog.CatalogService.CatalogFilter;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class ReportAndOpsController {

    public record CreateReportRequest(String substance, String purpose, String context,
                                      String design, String serotype, String phase) {}
    public record EnqueueJobRequest(@NotBlank String jobType, @NotBlank String refId, int maxAttempts) {}
    public record ReasonRequest(String reason) {}
    public record InboxDeliveryRequest(UUID eventId, @NotBlank String consumer) {}
    public record LeaseRequest(int leaseSeconds) {}
    public record CompleteJobRequest(UUID leaseToken) {}
    public record FailJobRequest(@NotBlank String errorMessage) {}

    private final ReportAndOpsService service;

    public ReportAndOpsController(ReportAndOpsService service) {
        this.service = service;
    }

    @PostMapping("/reports")
    @ResponseStatus(HttpStatus.CREATED)
    public Map<String, Object> createReport(@RequestBody(required = false) CreateReportRequest req,
                                            @AuthenticationPrincipal Jwt jwt) {
        CatalogFilter f = req == null ? new CatalogFilter(null, null, null, null, null, null)
                : new CatalogFilter(req.substance(), req.purpose(), req.context(), req.design(), req.serotype(), req.phase());
        return service.createSnapshot(f, UUID.fromString(jwt.getSubject()));
    }

    @GetMapping("/reports")
    public List<Map<String, Object>> listReports() {
        return service.listSnapshots();
    }

    @GetMapping("/reports/{id}")
    public Map<String, Object> getReport(@PathVariable UUID id) {
        return service.getSnapshot(id);
    }

    @GetMapping("/reports/{id}/export")
    public ResponseEntity<?> export(@PathVariable UUID id,
                                    @RequestParam(defaultValue = "json") String format) {
        return switch (format.toLowerCase()) {
            case "pdf" -> ResponseEntity.ok()
                    .contentType(MediaType.APPLICATION_PDF)
                    .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"relatorio-" + id + ".pdf\"")
                    .body(service.exportPdf(id));
            case "csv" -> ResponseEntity.ok()
                    .contentType(MediaType.parseMediaType("text/csv;charset=UTF-8"))
                    .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"relatorio-" + id + ".csv\"")
                    .body(service.exportCsv(id));
            default -> ResponseEntity.ok()
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(service.getSnapshot(id));
        };
    }

    @GetMapping("/ops/summary")
    @PreAuthorize("hasAnyRole('PESQUISADOR','ADJUDICADOR','ADMINISTRADOR')")
    public Map<String, Object> summary() {
        return service.operationalSummary();
    }

    @PostMapping("/ops/reassessments/{id}/resolve")
    @PreAuthorize("hasAnyRole('REVISOR','ADJUDICADOR','PESQUISADOR','ADMINISTRADOR')")
    public void resolveReassessment(@PathVariable UUID id,
                                    @RequestBody(required = false) ReasonRequest req,
                                    @AuthenticationPrincipal Jwt jwt) {
        service.resolveReassessment(id, req == null ? null : req.reason(), UUID.fromString(jwt.getSubject()));
    }

    @PostMapping("/ops/jobs")
    @ResponseStatus(HttpStatus.CREATED)
    @PreAuthorize("hasRole('ADMINISTRADOR')")
    public Map<String, Object> enqueueJob(@Valid @RequestBody EnqueueJobRequest req,
                                          @AuthenticationPrincipal Jwt jwt) {
        return service.enqueueJob(req.jobType(), req.refId(), req.maxAttempts(), UUID.fromString(jwt.getSubject()));
    }

    @PostMapping("/ops/jobs/{id}/retry")
    @PreAuthorize("hasRole('ADMINISTRADOR')")
    public Map<String, Object> retryJob(@PathVariable UUID id,
                                        @RequestBody(required = false) ReasonRequest req,
                                        @AuthenticationPrincipal Jwt jwt) {
        return service.retryJob(id, req == null ? null : req.reason(), UUID.fromString(jwt.getSubject()));
    }

    @PostMapping("/ops/outbox/relay")
    @PreAuthorize("hasAnyRole('PESQUISADOR','ADMINISTRADOR')")
    public Map<String, Object> relayOutbox(@RequestParam(defaultValue = "50") int limit) {
        return service.relayOutboxBatch(limit);
    }

    @PostMapping("/ops/inbox/register")
    @PreAuthorize("hasAnyRole('PESQUISADOR','ADMINISTRADOR')")
    public Map<String, Object> registerInbox(@Valid @RequestBody InboxDeliveryRequest req) {
        boolean firstDelivery = service.registerInboxDelivery(req.eventId(), req.consumer());
        return Map.of("eventId", req.eventId(), "consumer", req.consumer(), "firstDelivery", firstDelivery);
    }

    @PostMapping("/ops/jobs/{id}/lease")
    @PreAuthorize("hasAnyRole('PESQUISADOR','ADMINISTRADOR')")
    public Map<String, Object> acquireLease(@PathVariable UUID id,
                                            @RequestBody(required = false) LeaseRequest req) {
        return service.acquireLease(id, req == null ? 60 : req.leaseSeconds());
    }

    @PostMapping("/ops/jobs/{id}/complete")
    @PreAuthorize("hasAnyRole('PESQUISADOR','ADMINISTRADOR')")
    public void completeJob(@PathVariable UUID id, @Valid @RequestBody CompleteJobRequest req) {
        service.completeJobWithLease(id, req.leaseToken());
    }

    @PostMapping("/ops/jobs/{id}/fail")
    @PreAuthorize("hasAnyRole('PESQUISADOR','ADMINISTRADOR')")
    public Map<String, Object> failJob(@PathVariable UUID id, @Valid @RequestBody FailJobRequest req) {
        return service.failJob(id, req.errorMessage());
    }

    @GetMapping("/admin/reproduction-package")
    @PreAuthorize("hasRole('ADMINISTRADOR')")
    public Map<String, Object> reproductionPackage() {
        return service.exportReproductionPackage();
    }
}

