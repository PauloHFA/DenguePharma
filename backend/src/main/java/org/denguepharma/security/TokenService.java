package org.denguepharma.security;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.List;
import org.denguepharma.user.AppUser;
import org.denguepharma.user.Role;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.JwsHeader;
import org.springframework.security.oauth2.jwt.JwtClaimsSet;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.JwtEncoderParameters;
import org.springframework.stereotype.Service;

@Service
public class TokenService {

    private final JwtEncoder encoder;
    private final SecurityProperties props;

    public TokenService(JwtEncoder encoder, SecurityProperties props) {
        this.encoder = encoder;
        this.props = props;
    }

    public String issue(AppUser user) {
        Instant now = Instant.now();
        List<String> roles = user.getRoles().stream().map(Role::name).sorted().toList();
        JwtClaimsSet claims = JwtClaimsSet.builder()
                .issuer("denguepharma")
                .subject(user.getId().toString())
                .issuedAt(now)
                .expiresAt(now.plus(props.jwtTtlMinutes(), ChronoUnit.MINUTES))
                .claim("email", user.getEmail())
                .claim("roles", roles)
                .build();
        return encoder.encode(JwtEncoderParameters.from(
                JwsHeader.with(MacAlgorithm.HS256).build(), claims)).getTokenValue();
    }
}

