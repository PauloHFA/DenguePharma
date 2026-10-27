package org.denguepharma.protocol;

import com.fasterxml.jackson.databind.JsonNode;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.time.LocalDate;
import java.util.List;
import java.util.UUID;
import org.denguepharma.protocol.ProtocolService.ProtocolInput;
import org.denguepharma.protocol.ProtocolService.ProtocolView;
import org.springframework.http.HttpStatus;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/protocols")
@PreAuthorize("hasAnyRole('PESQUISADOR','ADMINISTRADOR')")
public class ProtocolController {

    public record ProtocolRequest(
            @NotBlank String code,
            @NotBlank String title,
            @NotBlank String question,
            @NotNull JsonNode sources,
            @NotNull JsonNode strategy,
            @NotNull JsonNode eligibility,
            @NotNull LocalDate cutoffDate) {
        ProtocolInput toInput() {
            return new ProtocolInput(code, title, question, sources, strategy, eligibility, cutoffDate);
        }
    }

    public record NewVersionRequest(String reason) {}

    private final ProtocolService service;

    public ProtocolController(ProtocolService service) {
        this.service = service;
    }

    @GetMapping
    public List<ProtocolView> list() {
        return service.list();
    }

    @GetMapping("/{id}")
    public ProtocolView get(@PathVariable UUID id) {
        return service.get(id);
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ProtocolView create(@Valid @RequestBody ProtocolRequest req, @AuthenticationPrincipal Jwt jwt) {
        return service.create(req.toInput(), UUID.fromString(jwt.getSubject()));
    }

    @PutMapping("/{id}")
    public ProtocolView update(@PathVariable UUID id, @Valid @RequestBody ProtocolRequest req,
                               @AuthenticationPrincipal Jwt jwt) {
        return service.update(id, req.toInput(), UUID.fromString(jwt.getSubject()));
    }

    @PostMapping("/{id}/register")
    public ProtocolView register(@PathVariable UUID id, @AuthenticationPrincipal Jwt jwt) {
        return service.register(id, UUID.fromString(jwt.getSubject()));
    }

    @PostMapping("/{id}/freeze")
    public ProtocolView freeze(@PathVariable UUID id, @AuthenticationPrincipal Jwt jwt) {
        return service.freeze(id, UUID.fromString(jwt.getSubject()));
    }

    @PostMapping("/{id}/new-version")
    @ResponseStatus(HttpStatus.CREATED)
    public ProtocolView newVersion(@PathVariable UUID id, @RequestBody(required = false) NewVersionRequest req,
                                   @AuthenticationPrincipal Jwt jwt) {
        return service.newVersion(id, req == null ? null : req.reason(), UUID.fromString(jwt.getSubject()));
    }
}

