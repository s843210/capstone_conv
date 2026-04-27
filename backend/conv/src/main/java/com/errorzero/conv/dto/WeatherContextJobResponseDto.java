package com.errorzero.conv.dto;

import lombok.Builder;
import lombok.Getter;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Getter
@Builder
public class WeatherContextJobResponseDto {
    private String runId;
    private String status;
    private LocalDate targetDate;
    private boolean dryRun;
    private Double avgTempC;
    private Double precipitationMm;
    private Short isRain;
    private LocalDateTime updatedAt;
    private String message;
}
