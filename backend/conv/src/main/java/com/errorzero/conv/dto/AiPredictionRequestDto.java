package com.errorzero.conv.dto;

import lombok.Getter;
import lombok.NoArgsConstructor;
import java.time.LocalDate;
import java.util.List;

@Getter
@NoArgsConstructor
public class AiPredictionRequestDto {
    
    private LocalDate targetDate;
    private List<PredictionItem> predictions;

    @Getter
    @NoArgsConstructor
    public static class PredictionItem {
        private String pluCode;
        private int predictedSales;
        private int recommendedOrder;
        private Double confidenceScore;
        private String aiInsight;
    }
}
