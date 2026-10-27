package org.denguepharma.security;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.denguepharma.audit.AuditService;
import org.denguepharma.user.AppUser;
import org.denguepharma.user.UserRepository;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    public record LoginRequest(@NotBlank String email, @NotBlank String password) {}
    public record LoginResponse(String token, String tokenType) {}
    public record MeResponse(String id, String email, List<String> roles) {}

    private final UserRepository users;
    private final PasswordEncoder encoder;
    private final TokenService tokens;
    private final AuditService audit;
    // Hash de senha aleatória, usado para igualar o tempo de resposta quando o usuário não existe.
    private final String dummyHash;

    public AuthController(UserRepository users, PasswordEncoder encoder, TokenService tokens, AuditService audit) {
        this.users = users;
        this.encoder = encoder;
        this.tokens = tokens;
        this.audit = audit;
        this.dummyHash = encoder.encode(UUID.randomUUID().toString());
    }

    @PostMapping("/login")
    public ResponseEntity<LoginResponse> login(@Valid @RequestBody LoginRequest req) {
        Optional<AppUser> found = users.findByEmailIgnoreCase(req.email());
        String hash = found.map(AppUser::getPasswordHash).orElse(dummyHash);
        boolean ok = encoder.matches(req.password(), hash) && found.map(AppUser::isActive).orElse(false);
        if (!ok) {
            audit.record(null, "LOGIN_FAILED", "app_user", null, null, null, null);
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }
        AppUser user = found.get();
        audit.record(user.getId(), "LOGIN", "app_user", user.getId().toString(), null, null, null);
        return ResponseEntity.ok(new LoginResponse(tokens.issue(user), "Bearer"));
    }

    @GetMapping("/me")
    public MeResponse me(@AuthenticationPrincipal Jwt jwt) {
        return new MeResponse(jwt.getSubject(), jwt.getClaimAsString("email"), jwt.getClaimAsStringList("roles"));
    }
}
