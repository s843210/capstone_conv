package com.errorzero.conv.dto;

import lombok.Builder;
import lombok.Getter;

import java.time.LocalDate;
import java.util.List;

@Getter
@Builder
public class SalesUploadResponseDto {
    private String runId;
    private boolean dryRun;
    private int salesFileCount;
    private int masterFileCount;
    private int rawRowCount;
    private int matchedRowCount;
    private int unmatchedRowCount;
    private int uniqueDailySalesCount;
    private int insertedCount;
    private int updatedCount;
    private int upsertedCount;
    private LocalDate minSalesDate;
    private LocalDate maxSalesDate;
    private List<String> unmatchedSamples;
    private String message;
}
