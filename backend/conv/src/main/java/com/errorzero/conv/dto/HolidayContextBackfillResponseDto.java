package com.errorzero.conv.dto;

import lombok.Builder;
import lombok.Getter;

import java.time.LocalDate;
import java.util.List;

@Getter
@Builder
public class HolidayContextBackfillResponseDto {
    private String runId;
    private String status;
    private LocalDate from;
    private LocalDate to;
    private int successCount;
    private int failureCount;
    private List<String> errors;
}
