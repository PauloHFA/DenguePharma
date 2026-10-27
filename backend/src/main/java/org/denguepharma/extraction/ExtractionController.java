package org.denguepharma.extraction;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.denguepharma.extraction.ExtractionService.ProposedField;
import org.denguepharma.extraction.ExtractionService.ReviewInput;
import org.denguepharma.extraction.ExtractionService.RunInput;
import org.springframework.http.HttpStatus;
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

@RestController
@RequestMapping("/api/extractions")
public class ExtractionController {

    public record SubmitRunRequest(
            @NotNull UUID documentVersionId,
            @NotBlank String pipelineVersion,
            @NotBlank String modelProvider,
            @NotBlank String modelVersion,
            @NotBlank String promptHash,
            String executionVariant,
            @NotBlank String schemaVersion,
            @NotNull List<ProposedField> fields) {}

    public record ReviewFieldRequest(
            @NotBlank String decision,
            String correctedValue,
            String correctedAbsenceStatus,
            String reason,
            boolean adjudication,
            boolean publishAfterApproval) {}

    private final ExtractionService service;

    public ExtractionController(ExtractionService service) {
        this.service = service;
    }

    @PostMapping("/runs")
    @ResponseStatus(HttpStatus.CREATED)
    @PreAuthorize("hasAnyRole('PESQUISADOR','REVISOR','ADJUDICADOR','ADMINISTRADOR')")
    public Map<String, Object> submitRun(@Valid @RequestBody SubmitRunRequest req,
                                         @AuthenticationPrincipal Jwt jwt) {
        return service.submitExtraction(new RunInput(
                req.documentVersionId(), req.pipelineVersion(), req.modelProvider(),
                req.modelVersion(), req.promptHash(), req.executionVariant(),
                req.schemaVersion(), req.fields()), UUID.fromString(jwt.getSubject()));
    }

    @GetMapping("/fields")
    @PreAuthorize("hasAnyRole('REVISOR','ADJUDICADOR','PESQUISADOR','ADMINISTRADOR')")
    public List<Map<String, Object>> listFields() {
        return service.listFieldsForReview();
    }

    @PostMapping("/fields/{id}/review")
    @PreAuthorize("hasAnyRole('REVISOR','ADJUDICADOR','ADMINISTRADOR')")
    public Map<String, Object> review(@PathVariable UUID id, @Valid @RequestBody ReviewFieldRequest req,
                                      @AuthenticationPrincipal Jwt jwt) {
        List<String> roles = jwt.getClaimAsStringList("roles");
        boolean isAdjudicator = roles != null && (roles.contains("ADJUDICADOR") || roles.contains("ADMINISTRADOR"));
        return service.reviewField(new ReviewInput(id, req.decision(), req.correctedValue(),
                req.correctedAbsenceStatus(), req.reason(), req.adjudication(), req.publishAfterApproval()),
                UUID.fromString(jwt.getSubject()), isAdjudicator);
    }
}

