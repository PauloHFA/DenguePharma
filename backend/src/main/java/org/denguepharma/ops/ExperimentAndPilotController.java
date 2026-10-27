package org.denguepharma.ops;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.util.Map;
import java.util.UUID;
import org.denguepharma.ops.ExperimentAndPilotService.TimingSessionInput;
import org.springframework.http.HttpStatus;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class ExperimentAndPilotController {

    public record CrossoverAllocateRequest(@NotNull UUID reviewer1, @NotNull UUID reviewer2) {}
    public record CreateTimingSessionRequest(
            @NotNull UUID documentVersionId,
            @NotBlank String conditionCode,
            int activeSeconds,
            int pauseSeconds,
            int correctionsCount,
            int criticalErrorsCount,
            String documentDifficulty) {}

    private final ExperimentAndPilotService service;

    public ExperimentAndPilotController(ExperimentAndPilotService service) {
        this.service = service;
    }

    @PostMapping("/experiment/split")
    @PreAuthorize("hasAnyRole('PESQUISADOR','ADMINISTRADOR')")
    public Map<String, Object> splitByFamily(@AuthenticationPrincipal Jwt jwt) {
        return service.partitionByStudyFamily(UUID.fromString(jwt.getSubject()));
    }

    @PostMapping("/experiment/allocate")
    @PreAuthorize("hasAnyRole('PESQUISADOR','ADMINISTRADOR')")
    public Map<String, Object> allocateCrossover(@Valid @RequestBody CrossoverAllocateRequest req,
                                                 @AuthenticationPrincipal Jwt jwt) {
        return service.allocateCrossoverBlocks(req.reviewer1(), req.reviewer2(), UUID.fromString(jwt.getSubject()));
    }

    @PostMapping("/experiment/sessions")
    @ResponseStatus(HttpStatus.CREATED)
    @PreAuthorize("hasAnyRole('REVISOR','ADJUDICADOR','PESQUISADOR','ADMINISTRADOR')")
    public Map<String, Object> recordSession(@Valid @RequestBody CreateTimingSessionRequest req,
                                             @AuthenticationPrincipal Jwt jwt) {
        return service.recordTimingSession(new TimingSessionInput(
                req.documentVersionId(), req.conditionCode(), req.activeSeconds(),
                req.pauseSeconds(), req.correctionsCount(), req.criticalErrorsCount(),
                req.documentDifficulty()), UUID.fromString(jwt.getSubject()));
    }

    @GetMapping("/experiment/metrics")
    @PreAuthorize("hasAnyRole('PESQUISADOR','ADJUDICADOR','ADMINISTRADOR')")
    public Map<String, Object> metrics() {
        return service.computeExperimentalMetrics();
    }

    @PostMapping("/admin/seed-pilot")
    @PreAuthorize("hasAnyRole('PESQUISADOR','ADMINISTRADOR')")
    public Map<String, Object> seedPilot(@AuthenticationPrincipal Jwt jwt) {
        return service.seedPilotCorpus(UUID.fromString(jwt.getSubject()));
    }
}

