package org.denguepharma.catalog;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.denguepharma.catalog.CatalogService.CatalogFilter;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/catalog")
public class CatalogController {

    public record CompareRequest(@NotEmpty List<UUID> studyIds) {}
    public record RetractRequest(@NotBlank String reason) {}

    private final CatalogService service;

    public CatalogController(CatalogService service) {
        this.service = service;
    }

    @GetMapping
    public List<Map<String, Object>> search(
            @RequestParam(required = false) String substance,
            @RequestParam(required = false) String purpose,
            @RequestParam(required = false) String context,
            @RequestParam(required = false) String design,
            @RequestParam(required = false) String serotype,
            @RequestParam(required = false) String phase) {
        return service.search(new CatalogFilter(substance, purpose, context, design, serotype, phase));
    }

    @PostMapping("/compare")
    public Map<String, Object> compare(@Valid @RequestBody CompareRequest req) {
        return service.compare(req.studyIds());
    }

    @PostMapping("/studies/{id}/retract")
    @PreAuthorize("hasAnyRole('ADJUDICADOR','PESQUISADOR','ADMINISTRADOR')")
    public Map<String, Object> retract(@PathVariable UUID id, @Valid @RequestBody RetractRequest req,
                                       @AuthenticationPrincipal Jwt jwt) {
        return service.retractStudy(id, req.reason(), UUID.fromString(jwt.getSubject()));
    }
}
