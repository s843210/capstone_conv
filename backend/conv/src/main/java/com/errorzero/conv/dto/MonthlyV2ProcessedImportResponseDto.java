package com.errorzero.conv.dto;

import lombok.Builder;
import lombok.Getter;

import java.time.LocalDate;
import java.util.List;

@Getter
@Builder
public class MonthlyV2ProcessedImportResponseDto {

    private String runId;
    private boolean dryRun;
    private String sourcePath;
    private long parsedRows;
    private long dailySalesUpsertedRows;
    private int productUpsertedRows;
    private int contextUpsertedRows;
    private int invalidRows;
    private LocalDate minDate;
    private LocalDate maxDate;
    private int uniquePluCount;
    private List<String> invalidSamples;
    private String message;
}
