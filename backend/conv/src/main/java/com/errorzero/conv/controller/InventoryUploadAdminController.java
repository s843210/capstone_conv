package com.errorzero.conv.controller;

import com.errorzero.conv.dto.InventoryUploadResponseDto;
import com.errorzero.conv.service.inventory.InventoryUploadService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/admin/inventory")
@RequiredArgsConstructor
@Validated
@Tag(name = "Inventory Upload Admin API", description = "재고 엑셀/CSV를 PLU 기준으로 product.current_stock에 반영하는 API")
public class InventoryUploadAdminController {

    private final InventoryUploadService inventoryUploadService;

    @Operation(summary = "현재고 업로드/반영", description = "PLU코드, 상품명, 현재고 컬럼을 읽어 활성 상품의 current_stock을 업데이트합니다.")
    @PostMapping(value = "/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<InventoryUploadResponseDto> uploadInventory(
            @RequestPart("file") MultipartFile file,
            @RequestParam(defaultValue = "false") boolean dryRun
    ) {
        InventoryUploadResponseDto response = inventoryUploadService.upload(file, dryRun);
        return ResponseEntity.ok(response);
    }
}
