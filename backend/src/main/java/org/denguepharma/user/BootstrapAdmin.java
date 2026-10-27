package org.denguepharma.user;

import java.util.EnumSet;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

/** Cria o primeiro administrador a partir de variáveis de ambiente, apenas se não existir nenhum usuário. */
@Component
public class BootstrapAdmin implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(BootstrapAdmin.class);

    private final UserRepository users;
    private final PasswordEncoder encoder;
    private final String email;
    private final String password;

    public BootstrapAdmin(UserRepository users, PasswordEncoder encoder,
                          @Value("${denguepharma.bootstrap.admin-email:}") String email,
                          @Value("${denguepharma.bootstrap.admin-password:}") String password) {
        this.users = users;
        this.encoder = encoder;
        this.email = email;
        this.password = password;
    }

    @Override
    public void run(ApplicationArguments args) {
        if (users.count() > 0 || email.isBlank() || password.isBlank()) {
            return;
        }
        if (password.length() < 12) {
            throw new IllegalStateException("BOOTSTRAP_ADMIN_PASSWORD deve ter ao menos 12 caracteres");
        }
        users.save(new AppUser(email, encoder.encode(password), "Administrador",
                EnumSet.of(Role.ADMINISTRADOR)));
        log.info("Administrador inicial criado: {}", email);
    }
}

