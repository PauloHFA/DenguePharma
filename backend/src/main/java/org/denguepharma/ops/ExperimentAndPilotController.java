package org.denguepharma.ops;

import java.util.Map;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

/** Os dados experimentais v1 sao historicos; o MVP v2 produz analises descritivas. */
@RestController
@RequestMapping("/api")
public class ExperimentAndPilotController {
    private final ExperimentAndPilotService service;
    public ExperimentAndPilotController(ExperimentAndPilotService service) { this.service=service; }
    @PostMapping({"/experiment/split", "/experiment/allocate", "/experiment/sessions"})
    public void retiredMutation() { retired(); }
    @GetMapping("/experiment/metrics")
    public void retiredMetrics() { retired(); }
    private void retired() {
        throw new ResponseStatusException(HttpStatus.GONE,
                "Experimento de IA retirado do MVP v2. Registros historicos preservados; utilize /api/analyses para analise descritiva.");
    }
    @PostMapping("/admin/seed-pilot")
    @PreAuthorize("hasRole('ADMINISTRADOR')")
    public Map<String,Object> seed(@AuthenticationPrincipal Jwt jwt) { return service.seedPilotCorpus(UUID.fromString(jwt.getSubject())); }
}
