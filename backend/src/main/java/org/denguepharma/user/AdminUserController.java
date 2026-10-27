package org.denguepharma.user;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Size;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import org.denguepharma.audit.AuditService;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

/** Administração de acesso (RF-12). Restrito a ADMINISTRADOR em SecurityConfig. */
@RestController
@RequestMapping("/api/admin/users")
public class AdminUserController {

    public record CreateUserRequest(
            @NotBlank @Email String email,
            @NotBlank @Size(min = 12, message = "senha deve ter ao menos 12 caracteres") String password,
            @NotBlank String displayName,
            @NotEmpty Set<Role> roles) {}

    public record UserView(UUID id, String email, String displayName, boolean active, List<String> roles) {
        static UserView of(AppUser u) {
            return new UserView(u.getId(), u.getEmail(), u.getDisplayName(), u.isActive(),
                    u.getRoles().stream().map(Role::name).sorted().toList());
        }
    }

    private final UserRepository users;
    private final PasswordEncoder encoder;
    private final AuditService audit;

    public AdminUserController(UserRepository users, PasswordEncoder encoder, AuditService audit) {
        this.users = users;
        this.encoder = encoder;
        this.audit = audit;
    }

    @GetMapping
    public List<UserView> list() {
        return users.findAll().stream().map(UserView::of).toList();
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    @Transactional
    public UserView create(@Valid @RequestBody CreateUserRequest req, @AuthenticationPrincipal Jwt jwt) {
        if (users.findByEmailIgnoreCase(req.email()).isPresent()) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "email ja cadastrado");
        }
        AppUser saved = users.save(new AppUser(req.email(), encoder.encode(req.password()),
                req.displayName(), req.roles()));
        audit.record(UUID.fromString(jwt.getSubject()), "USER_CREATED", "app_user", saved.getId().toString(),
                null, "{\"email\":\"" + saved.getEmail().replace("\"", "") + "\",\"roles\":\""
                        + saved.getRoles() + "\"}", null);
        return UserView.of(saved);
    }
}

