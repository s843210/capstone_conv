package com.errorzero.conv.dto;

import lombok.Builder;
import lombok.Getter;

import java.util.List;

@Getter
@Builder
public class ProductMasterUploadResponseDto {
    private String runId;
    private boolean dryRun;
    private int fileCount;
    private int rawRowCount;
    private int parsedRowCount;
    private int duplicatePluCount;
    private int upsertedCount;
    private List<String> duplicateSamples;
    private List<String> fileSamples;
    private String message;
}
