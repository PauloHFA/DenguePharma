package org.denguepharma.security;

import java.util.HashMap;
import java.util.Map;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.server.ResponseStatusException;

/**
 * Tratamento global de exceções conforme RFC 7807 (ProblemDetail).
 * Preserva mensagens de validação e códigos HTTP padronizados para guiar clientes e frontend.
 */
@RestControllerAdvice
public class ApiExceptionHandler {

    @ExceptionHandler(ResponseStatusException.class)
    public ProblemDetail handleResponseStatus(ResponseStatusException error) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(error.getStatusCode(),
                error.getReason() == null ? "Operação não permitida" : error.getReason());
        problem.setTitle("Erro de Requisição");
        return problem;
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ProblemDetail handleValidation(MethodArgumentNotValidException error) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST,
                "Erro de validação nos campos da requisição");
        problem.setTitle("Dados Inválidos");
        Map<String, String> fieldErrors = new HashMap<>();
        for (FieldError fe : error.getBindingResult().getFieldErrors()) {
            fieldErrors.put(fe.getField(), fe.getDefaultMessage());
        }
        problem.setProperty("invalidParams", fieldErrors);
        return problem;
    }

    @ExceptionHandler(AccessDeniedException.class)
    public ProblemDetail handleAccessDenied(AccessDeniedException error) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.FORBIDDEN,
                "Acesso negado: permissão insuficiente para executar esta operação");
        problem.setTitle("Acesso Não Autorizado");
        return problem;
    }

    @ExceptionHandler(DataIntegrityViolationException.class)
    public ProblemDetail handleDataIntegrity(DataIntegrityViolationException error) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT,
                "Violação de integridade de dados (registro duplicado ou chave/vínculo inválido)");
        problem.setTitle("Conflito de Integridade");
        return problem;
    }

    @ExceptionHandler(IllegalArgumentException.class)
    public ProblemDetail handleIllegalArgument(IllegalArgumentException error) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST,
                error.getMessage() == null ? "Parâmetro inválido fornecido" : error.getMessage());
        problem.setTitle("Parâmetro Inválido");
        return problem;
    }
}
