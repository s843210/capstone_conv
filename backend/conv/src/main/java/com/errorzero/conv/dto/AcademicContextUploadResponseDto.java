package com.errorzero.conv.dto;

import lombok.Builder;
import lombok.Getter;

import java.time.LocalDate;
import java.util.List;

@Getter
@Builder
public class AcademicContextUploadResponseDto {
    private String runId;
    private boolean dryRun;
    private int parsedRuleRows;
    private int savedRuleRows;
    private int invalidRuleRows;
    private int ignoredRuleRows;
    private Integer monday;
    private Integer tuesday;
    private Integer wednesday;
    private Integer thursday;
    private Integer friday;
    private Integer defaultCount;
    private LocalDate minRuleDate;
    private LocalDate maxRuleDate;
    private List<String> invalidSamples;
    private String message;
}
