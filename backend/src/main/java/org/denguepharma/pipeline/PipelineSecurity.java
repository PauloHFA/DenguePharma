package org.denguepharma.pipeline;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.List;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;

/** Credencial de servico restrita as rotas internas; nunca confere acesso de usuario/admin. */
public class PipelineSecurity extends OncePerRequestFilter {
    private final byte[] token;
    public PipelineSecurity(String token) {
        this.token = token.getBytes(StandardCharsets.UTF_8);
        if (!token.isEmpty() && token.length() < 32) throw new IllegalArgumentException("PIPELINE_TOKEN exige 32 caracteres");
    }
    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        return !request.getRequestURI().startsWith(request.getContextPath() + "/api/internal/pipeline/");
    }
    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws IOException, ServletException {
        String presented = request.getHeader("X-Pipeline-Token");
        if (token.length >= 32 && presented != null
                && MessageDigest.isEqual(token, presented.getBytes(StandardCharsets.UTF_8))) {
            var context = SecurityContextHolder.createEmptyContext();
            context.setAuthentication(new UsernamePasswordAuthenticationToken("pipeline-worker", null,
                    List.of(new SimpleGrantedAuthority("ROLE_PIPELINE_WORKER"))));
            SecurityContextHolder.setContext(context);
        }
        chain.doFilter(request, response);
    }
}
