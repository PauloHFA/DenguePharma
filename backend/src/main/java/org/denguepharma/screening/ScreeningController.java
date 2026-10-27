package org.denguepharma.screening;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.denguepharma.screening.ScreeningService.DecisionInput;
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
@RequestMapping("/api/screening")
public class ScreeningController {

    public record ScreeningDecisionRequest(
            @NotNull UUID studyId,
            @NotBlank String stage,
            @NotBlank String decision,
            String exclusionCategory,
            String exclusionReason,
            String context,
            String purpose,
            boolean withoutPostedResults,
            boolean adjudication) {}

    private final ScreeningService service;

    public ScreeningController(ScreeningService service) {
        this.service = service;
    }

    @GetMapping("/studies")
    @PreAuthorize("hasAnyRole('REVISOR','ADJUDICADOR','PESQUISADOR','ADMINISTRADOR')")
    public List<Map<String, Object>> queue(@AuthenticationPrincipal Jwt jwt) {
        List<String> roles = jwt.getClaimAsStringList("roles");
        boolean isAdjudicator = roles != null && (roles.contains("ADJUDICADOR") || roles.contains("ADMINISTRADOR"));
        return service.queue(UUID.fromString(jwt.getSubject()), isAdjudicator);
    }

    @PostMapping("/decisions")
    @ResponseStatus(HttpStatus.CREATED)
    @PreAuthorize("hasAnyRole('REVISOR','ADJUDICADOR','PESQUISADOR','ADMINISTRADOR')")
    public Map<String, Object> decide(@Valid @RequestBody ScreeningDecisionRequest req,
                                      @AuthenticationPrincipal Jwt jwt) {
        List<String> roles = jwt.getClaimAsStringList("roles");
        boolean canAdjudicate = roles != null && (roles.contains("ADJUDICADOR") || roles.contains("ADMINISTRADOR"));
        return service.recordDecision(new DecisionInput(req.studyId(), req.stage(), req.decision(),
                req.exclusionCategory(), req.exclusionReason(), req.context(), req.purpose(),
                req.withoutPostedResults(), req.adjudication()), UUID.fromString(jwt.getSubject()), canAdjudicate);
    }

    @GetMapping("/flowchart")
    public Map<String, Object> flowchart() {
        return service.prismaFlowchart();
    }
}

