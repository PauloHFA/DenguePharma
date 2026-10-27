package org.denguepharma.substance;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.denguepharma.substance.StudyLinkService.ProposeRequest;
import org.denguepharma.substance.SubstanceService.SubstanceInput;
import org.denguepharma.substance.SubstanceService.SubstanceView;
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
@RequestMapping("/api")
public class SubstanceAndLinkController {

    public record CreateSubstanceRequest(@NotBlank String publishedName, String productType,
                                         boolean combination, List<UUID> componentIds) {}
    public record CreateProposalRequest(@NotNull UUID primaryStudyId, @NotNull UUID candidateStudyId,
                                        @NotBlank String sharedIdentifier, @NotBlank String idType,
                                        @NotBlank String reason) {}
    public record ApproveRequest(String reportRole) {}
    public record ReasonRequest(String reason) {}

    private final SubstanceService substances;
    private final StudyLinkService links;

    public SubstanceAndLinkController(SubstanceService substances, StudyLinkService links) {
        this.substances = substances;
        this.links = links;
    }

    @GetMapping("/substances")
    public List<SubstanceView> listSubstances() {
        return substances.list();
    }

    @PostMapping("/substances")
    @ResponseStatus(HttpStatus.CREATED)
    @PreAuthorize("hasAnyRole('REVISOR','ADJUDICADOR','PESQUISADOR','ADMINISTRADOR')")
    public SubstanceView createSubstance(@Valid @RequestBody CreateSubstanceRequest req,
                                         @AuthenticationPrincipal Jwt jwt) {
        return substances.create(new SubstanceInput(req.publishedName(), req.productType(),
                req.combination(), req.componentIds()), UUID.fromString(jwt.getSubject()));
    }

    @PostMapping("/substances/{id}/normalize")
    @PreAuthorize("hasAnyRole('REVISOR','ADJUDICADOR','PESQUISADOR','ADMINISTRADOR')")
    public SubstanceView normalize(@PathVariable UUID id, @AuthenticationPrincipal Jwt jwt) {
        return substances.normalizeWithPubChem(id, UUID.fromString(jwt.getSubject()));
    }

    @GetMapping("/study-links/proposals")
    @PreAuthorize("hasAnyRole('REVISOR','ADJUDICADOR','PESQUISADOR','ADMINISTRADOR')")
    public List<Map<String, Object>> listProposals() {
        return links.listProposals();
    }

    @PostMapping("/study-links/proposals")
    @ResponseStatus(HttpStatus.CREATED)
    @PreAuthorize("hasAnyRole('REVISOR','ADJUDICADOR','PESQUISADOR','ADMINISTRADOR')")
    public Map<String, Object> propose(@Valid @RequestBody CreateProposalRequest req,
                                       @AuthenticationPrincipal Jwt jwt) {
        return links.propose(new ProposeRequest(req.primaryStudyId(), req.candidateStudyId(),
                req.sharedIdentifier(), req.idType(), req.reason()), UUID.fromString(jwt.getSubject()));
    }

    @PostMapping("/study-links/proposals/{id}/approve")
    @PreAuthorize("hasAnyRole('ADJUDICADOR','PESQUISADOR','ADMINISTRADOR')")
    public void approve(@PathVariable UUID id, @RequestBody(required = false) ApproveRequest req,
                        @AuthenticationPrincipal Jwt jwt) {
        links.approve(id, req == null ? null : req.reportRole(), UUID.fromString(jwt.getSubject()));
    }

    @PostMapping("/study-links/proposals/{id}/reject")
    @PreAuthorize("hasAnyRole('ADJUDICADOR','PESQUISADOR','ADMINISTRADOR')")
    public void reject(@PathVariable UUID id, @RequestBody(required = false) ReasonRequest req,
                       @AuthenticationPrincipal Jwt jwt) {
        links.reject(id, req == null ? null : req.reason(), UUID.fromString(jwt.getSubject()));
    }

    @PostMapping("/study-links/proposals/{id}/undo")
    @PreAuthorize("hasAnyRole('ADJUDICADOR','PESQUISADOR','ADMINISTRADOR')")
    public void undo(@PathVariable UUID id, @RequestBody(required = false) ReasonRequest req,
                     @AuthenticationPrincipal Jwt jwt) {
        links.undo(id, req == null ? null : req.reason(), UUID.fromString(jwt.getSubject()));
    }
}

