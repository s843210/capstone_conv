package com.errorzero.conv.dto;

import lombok.Builder;
import lombok.Getter;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Getter
@Builder
public class AcademicContextJobResponseDto {
    private String runId;
    private String status;
    private LocalDate targetDate;
    private Integer academicEvent;
    private Integer buildingHeadcount;
    private LocalDateTime updatedAt;
    private String message;
}
