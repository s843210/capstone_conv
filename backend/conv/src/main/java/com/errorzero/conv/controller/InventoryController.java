package com.errorzero.conv.controller;

import com.errorzero.conv.dto.InventoryResponseDto;
import com.errorzero.conv.service.InventoryService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Pattern;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/inventory")
@RequiredArgsConstructor
@Validated
@Tag(name = "Inventory API", description = "재고 관리 화면 무한 스크롤용 API")
public class InventoryController {

    private final InventoryService inventoryService;

    @Operation(summary = "재고 페이징 조회", description = "재고가 적은 순서대로 무한 스크롤 형태의 재고 데이터를 30개씩 가져옵니다.")
    @GetMapping
    public ResponseEntity<InventoryResponseDto> getInventoryList(
            @RequestParam(defaultValue = "0") @Min(value = 0, message = "page는 0 이상이어야 합니다") int page,
            @RequestParam(defaultValue = "30") @Min(value = 1, message = "size는 1 이상이어야 합니다") @Max(value = 100, message = "size는 100 이하여야 합니다") int size,
            @RequestParam(defaultValue = "") String q,
            @RequestParam(defaultValue = "") String category,
            @RequestParam(defaultValue = "stock_asc") @Pattern(regexp = "stock_(asc|desc)", message = "sort는 stock_asc 또는 stock_desc만 가능합니다") String sort
    ) {
        return ResponseEntity.ok(inventoryService.getInventoryPage(page, size, q, category, sort));
    }

    @Operation(summary = "재고 카테고리 목록 조회", description = "재고 관리 필터에 사용할 활성 카테고리 목록을 조회합니다.")
    @GetMapping("/categories")
    public ResponseEntity<List<String>> getCategories() {
        return ResponseEntity.ok(inventoryService.getActiveCategories());
    }
}
