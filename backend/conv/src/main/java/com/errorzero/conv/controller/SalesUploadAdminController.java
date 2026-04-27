package com.errorzero.conv.controller;

import com.errorzero.conv.dto.SalesUploadResponseDto;
import com.errorzero.conv.service.sales.SalesUploadService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.time.LocalDate;
import java.util.List;

@RestController
@RequestMapping("/api/admin/sales")
@RequiredArgsConstructor
@Validated
@Tag(name = "Sales Upload Admin API", description = "판매 파일을 PLU 매칭 후 daily_sales 테이블에 적재하는 API")
public class SalesUploadAdminController {

    private final SalesUploadService salesUploadService;

    @Operation(summary = "판매량 업로드/적재", description = "판매파일(xlsx/csv)과 분류마스터(csv)를 받아 sales_date, plu_code, sales_qty를 daily_sales에 업서트합니다.")
    @PostMapping(value = "/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<SalesUploadResponseDto> uploadSales(
            @RequestPart("salesFiles") List<MultipartFile> salesFiles,
            @RequestPart("masterFiles") List<MultipartFile> masterFiles,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate salesDate,
            @RequestParam(defaultValue = "false") boolean dryRun
    ) {
        SalesUploadResponseDto response = salesUploadService.upload(salesFiles, masterFiles, salesDate, dryRun);
        return ResponseEntity.ok(response);
    }
}
