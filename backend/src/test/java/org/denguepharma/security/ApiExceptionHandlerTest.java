package org.denguepharma.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.validation.BindingResult;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.server.ResponseStatusException;

class ApiExceptionHandlerTest {

    private ApiExceptionHandler handler;

    @BeforeEach
    void setUp() {
        handler = new ApiExceptionHandler();
    }

    @Test
    @DisplayName("ResponseStatusException deve retornar status e detalhe especificados")
    void handleResponseStatus() {
        ResponseStatusException ex = new ResponseStatusException(HttpStatus.NOT_FOUND, "Recurso ausente");
        ProblemDetail problem = handler.handleResponseStatus(ex);

        assertThat(problem.getStatus()).isEqualTo(404);
        assertThat(problem.getDetail()).isEqualTo("Recurso ausente");
        assertThat(problem.getTitle()).isEqualTo("Erro de Requisição");
    }

    @Test
    @DisplayName("MethodArgumentNotValidException deve retornar 400 e invalidParams com campos")
    void handleValidation() {
        MethodArgumentNotValidException ex = mock(MethodArgumentNotValidException.class);
        BindingResult bindingResult = mock(BindingResult.class);
        FieldError fieldError = new FieldError("userDto", "email", "Email inválido");
        when(ex.getBindingResult()).thenReturn(bindingResult);
        when(bindingResult.getFieldErrors()).thenReturn(List.of(fieldError));

        ProblemDetail problem = handler.handleValidation(ex);

        assertThat(problem.getStatus()).isEqualTo(400);
        assertThat(problem.getTitle()).isEqualTo("Dados Inválidos");
        assertThat(problem.getProperties()).containsKey("invalidParams");
        @SuppressWarnings("unchecked")
        Map<String, String> invalidParams = (Map<String, String>) problem.getProperties().get("invalidParams");
        assertThat(invalidParams).containsEntry("email", "Email inválido");
    }

    @Test
    @DisplayName("AccessDeniedException deve retornar 403 Forbidden")
    void handleAccessDenied() {
        AccessDeniedException ex = new AccessDeniedException("Permissão negada");
        ProblemDetail problem = handler.handleAccessDenied(ex);

        assertThat(problem.getStatus()).isEqualTo(403);
        assertThat(problem.getTitle()).isEqualTo("Acesso Não Autorizado");
        assertThat(problem.getDetail()).contains("Acesso negado");
    }

    @Test
    @DisplayName("DataIntegrityViolationException deve retornar 409 Conflict")
    void handleDataIntegrity() {
        DataIntegrityViolationException ex = new DataIntegrityViolationException("Duplicate key");
        ProblemDetail problem = handler.handleDataIntegrity(ex);

        assertThat(problem.getStatus()).isEqualTo(409);
        assertThat(problem.getTitle()).isEqualTo("Conflito de Integridade");
        assertThat(problem.getDetail()).contains("Violação de integridade");
    }

    @Test
    @DisplayName("IllegalArgumentException deve retornar 400 Bad Request")
    void handleIllegalArgument() {
        IllegalArgumentException ex = new IllegalArgumentException("Argumento inválido de teste");
        ProblemDetail problem = handler.handleIllegalArgument(ex);

        assertThat(problem.getStatus()).isEqualTo(400);
        assertThat(problem.getTitle()).isEqualTo("Parâmetro Inválido");
        assertThat(problem.getDetail()).isEqualTo("Argumento inválido de teste");
    }
}
