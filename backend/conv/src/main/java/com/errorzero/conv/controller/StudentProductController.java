package com.errorzero.conv.controller;

import com.errorzero.conv.dto.StudentProductResponseDto;
import com.errorzero.conv.dto.StudentRequestCreateDto;
import com.errorzero.conv.dto.StudentRequestDashboardResponseDto;
import com.errorzero.conv.dto.StudentRequestResponseDto;
import com.errorzero.conv.service.StudentProductService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDate;
import java.util.List;

@RestController
@RequestMapping("/api/student")
@RequiredArgsConstructor
@Validated
@Tag(name = "Student App API", description = "학생 앱 상품 조회 및 신청 API")
public class StudentProductController {

    private final StudentProductService studentProductService;

    @Operation(summary = "학생 앱 상품 목록 조회", description = "daily_sales에 존재하는 상품 중 학생 앱에 보여줄 상품을 product와 조인해 조회합니다. category/keyword가 없으면 주먹밥 또는 김밥 상품을 기본 조회합니다.")
    @GetMapping("/products")
    public ResponseEntity<List<StudentProductResponseDto>> getProducts(
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate salesDate,
            @RequestParam(defaultValue = "") String category,
            @RequestParam(defaultValue = "") String keyword
    ) {
        return ResponseEntity.ok(studentProductService.getStudentProducts(salesDate, category, keyword));
    }

    @Operation(summary = "학생 신청 현황 조회", description = "대시보드에 표시할 학생별 신청 상품명, 원하는 수량, 학생 ID, 신청일시를 최신순으로 조회합니다.")
    @GetMapping("/requests")
    public ResponseEntity<List<StudentRequestDashboardResponseDto>> getRequests(
            @RequestParam(defaultValue = "100") @Min(1) @Max(500) int limit
    ) {
        return ResponseEntity.ok(studentProductService.getDashboardRequests(limit));
    }

    @Operation(summary = "학생 상품 신청 저장", description = "학생이 선택한 상품별 신청 수량을 저장합니다. 같은 학생/판매일/상품으로 다시 신청하면 수량을 갱신합니다.")
    @PostMapping("/requests")
    public ResponseEntity<StudentRequestResponseDto> submitRequest(
            @Valid @RequestBody StudentRequestCreateDto request
    ) {
        return ResponseEntity.ok(studentProductService.submitRequest(request));
    }
}
