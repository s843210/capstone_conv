package com.errorzero.conv.controller;

import com.errorzero.conv.dto.ProductMasterUploadResponseDto;
import com.errorzero.conv.service.inventory.ProductMasterUploadService;
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

import java.util.List;

@RestController
@RequestMapping("/api/admin/products/master")
@RequiredArgsConstructor
@Validated
@Tag(name = "Product Master Upload Admin API", description = "Uploads product master CSV files for PLU category mapping.")
public class ProductMasterUploadAdminController {

    private final ProductMasterUploadService productMasterUploadService;

    @Operation(summary = "Upload product master CSV files")
    @PostMapping(value = "/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<ProductMasterUploadResponseDto> uploadProductMaster(
            @RequestPart("files") List<MultipartFile> files,
            @RequestParam(defaultValue = "false") boolean dryRun
    ) {
        ProductMasterUploadResponseDto response = productMasterUploadService.upload(files, dryRun);
        return ResponseEntity.ok(response);
    }
}
