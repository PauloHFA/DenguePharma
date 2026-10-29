package org.denguepharma.security;

import org.springframework.http.ProblemDetail;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.server.ResponseStatusException;

/** Preserva a mensagem de validacao para que a interface indique como corrigir a operacao. */
@RestControllerAdvice
public class ApiExceptionHandler {
    @ExceptionHandler(ResponseStatusException.class)
    public ProblemDetail handle(ResponseStatusException error) {
        return ProblemDetail.forStatusAndDetail(error.getStatusCode(),
                error.getReason() == null ? "Operacao nao permitida" : error.getReason());
    }
}
