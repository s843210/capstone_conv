package com.errorzero.conv.controller;

import com.errorzero.conv.dto.AiRunResponseDto;
import com.errorzero.conv.service.AiRunAdminService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDate;

@RestController
@RequestMapping("/api/admin/ai")
@RequiredArgsConstructor
@Tag(name = "AI Run Admin API", description = "FastAPI 예측 실행과 ai_prediction 저장을 관리하는 API")
public class AiRunAdminController {

    private final AiRunAdminService aiRunAdminService;

    @Operation(summary = "AI 예측 실행")
    @PostMapping("/predict")
    public ResponseEntity<AiRunResponseDto> runPredict(
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate targetDate,
            @RequestParam(defaultValue = "true") boolean onlyPositiveRecommendations
    ) {
        AiRunResponseDto response = aiRunAdminService.runPredict(targetDate, onlyPositiveRecommendations);
        return ResponseEntity.ok(response);
    }
}
