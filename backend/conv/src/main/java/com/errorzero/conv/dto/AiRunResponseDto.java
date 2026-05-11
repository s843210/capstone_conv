package com.errorzero.conv.dto;

import lombok.Builder;
import lombok.Getter;

import java.time.LocalDate;

@Getter
@Builder
public class AiRunResponseDto {
    private String runId;
    private String status;
    private String modelName;
    private LocalDate targetDate;
    private int rowCount;
    private int savedCount;
    private String predictionCsv;
    private String recommendationCsv;
    private String errorMessage;
}
