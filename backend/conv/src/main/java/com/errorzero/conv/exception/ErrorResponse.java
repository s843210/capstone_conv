package com.errorzero.conv.exception;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;

import java.time.LocalDateTime;

/**
 * API 에러 응답의 통일된 포맷.
 */
@Getter
@Builder
@AllArgsConstructor
public class ErrorResponse {
    private final int status;
    private final String message;
    @Builder.Default
    private final LocalDateTime timestamp = LocalDateTime.now();
}
