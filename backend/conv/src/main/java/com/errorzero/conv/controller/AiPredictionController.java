package com.errorzero.conv.controller;

import com.errorzero.conv.dto.AiPredictionRequestDto;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/ai")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
@Tag(name = "AI Integration API", description = "FastAPI 서버에서 생성된 예측값을 수신하는 API")
public class AiPredictionController {

    @Operation(summary = "AI 예측 데이터 수신", description = "FastAPI에서 분석한 상품별 예상 판매량 및 권장 발주량을 DB에 저장합니다.")
    @PostMapping("/predictions")
    public ResponseEntity<String> receivePredictions(@RequestBody AiPredictionRequestDto requestDto) {
        // TODO: 향후 Service 레이어를 호출하여 DB(ai_prediction 테이블)에 저장하는 로직 추가
        return ResponseEntity.ok("AI 데이터 수신 및 저장 완료 (목업 응답)");
    }
}
