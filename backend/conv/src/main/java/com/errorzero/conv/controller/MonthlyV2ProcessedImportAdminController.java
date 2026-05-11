package com.errorzero.conv.controller;

import com.errorzero.conv.dto.MonthlyV2ProcessedImportResponseDto;
import com.errorzero.conv.service.sales.MonthlyV2ProcessedImportService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/admin/sales/monthly-v2")
@RequiredArgsConstructor
@Validated
@Tag(name = "Monthly V2 Processed Sales Import API", description = "monthly_v2 processed CSV를 DB 원천 테이블로 bulk import합니다.")
public class MonthlyV2ProcessedImportAdminController {

    private final MonthlyV2ProcessedImportService importService;

    @Operation(summary = "monthly_v2 processed CSV 경로 import", description = "설정된 CSV 경로를 읽어 daily_sales, daily_context, product에 upsert합니다.")
    @PostMapping("/import-processed")
    public ResponseEntity<MonthlyV2ProcessedImportResponseDto> importProcessed(
            @RequestParam(required = false) String path,
            @RequestParam(defaultValue = "true") boolean dryRun
    ) {
        MonthlyV2ProcessedImportResponseDto response = importService.importFromConfiguredPath(path, dryRun);
        return ResponseEntity.ok(response);
    }
}
