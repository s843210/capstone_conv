package com.errorzero.conv.controller;

import com.errorzero.conv.dto.DashboardResponseDto.MainDashboard;
import com.errorzero.conv.service.DashboardService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/dashboard")
@RequiredArgsConstructor
@Tag(name = "Dashboard API", description = "대시보드 메인 화면 관련 API (인사이트, 재고, 발주 추천)")
public class DashboardController {

    private final DashboardService dashboardService;

    @Operation(summary = "메인 대시보드 데이터 전체 조회", description = "점주가 가장 먼저 보는 대시보드 화면에 필요한 모든 요약 데이터를 한 번에 가져옵니다.")
    @GetMapping
    public ResponseEntity<MainDashboard> getMainDashboard() {
        MainDashboard dashboardData = dashboardService.getDashboardData();
        return ResponseEntity.ok(dashboardData);
    }
}
