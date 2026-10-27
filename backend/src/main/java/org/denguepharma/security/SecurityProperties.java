package org.denguepharma.security;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "denguepharma.security")
public record SecurityProperties(String jwtSecret, long jwtTtlMinutes) {

    public SecurityProperties {
        if (jwtSecret == null || jwtSecret.getBytes(java.nio.charset.StandardCharsets.UTF_8).length < 32) {
            throw new IllegalStateException("JWT_SECRET deve ter no minimo 32 caracteres");
        }
        if (jwtTtlMinutes <= 0) {
            jwtTtlMinutes = 60;
        }
    }
}

