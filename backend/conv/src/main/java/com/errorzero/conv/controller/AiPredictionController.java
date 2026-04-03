package com.errorzero.conv.controller;

import com.errorzero.conv.dto.AiPredictionRequestDto;
import com.errorzero.conv.service.AiPredictionService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/ai")
@RequiredArgsConstructor
@Tag(name = "AI Integration API", description = "FastAPI 서버에서 생성된 예측값을 수신하는 API")
public class AiPredictionController {

    private final AiPredictionService aiPredictionService;

    @Operation(summary = "AI 예측 데이터 수신", description = "FastAPI에서 분석한 상품별 예상 판매량 및 권장 발주량을 DB에 저장합니다. 현재 재고에 없는 상품은 무시됩니다.")
    @PostMapping("/predictions")
    public ResponseEntity<Map<String, Object>> receivePredictions(@Valid @RequestBody AiPredictionRequestDto requestDto) {
        int savedCount = aiPredictionService.savePredictions(requestDto);
        return ResponseEntity.ok(Map.of(
                "message", "AI 데이터 수신 및 저장 완료",
                "savedCount", savedCount
        ));
    }
}
