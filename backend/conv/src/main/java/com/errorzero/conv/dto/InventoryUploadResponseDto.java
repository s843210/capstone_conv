package com.errorzero.conv.dto;

import lombok.Builder;
import lombok.Getter;

import java.util.List;

@Getter
@Builder
public class InventoryUploadResponseDto {
    private String runId;
    private boolean dryRun;
    private String fileName;
    private int rawRowCount;
    private int parsedRowCount;
    private int duplicatePluCount;
    private int negativeStockNormalizedCount;
    private int matchedCount;
    private int createdOrUpdatedProductCount;
    private int masterMatchedCount;
    private int masterUnmatchedCount;
    private int snapshotUpsertedCount;
    private int updatedCount;
    private int skippedCount;
    private int nameMismatchCount;
    private List<String> skippedSamples;
    private List<String> nameMismatchSamples;
    private String message;
}
