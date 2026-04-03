package com.errorzero.conv.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.util.List;

@Getter
@NoArgsConstructor
public class AiPredictionRequestDto {

    @NotNull(message = "예측 대상 날짜는 필수입니다")
    private LocalDate targetDate;

    @NotEmpty(message = "카테고리 목록은 비어있을 수 없습니다")
    @Valid
    private List<CategoryPrediction> categories;

    @Getter
    @NoArgsConstructor
    public static class CategoryPrediction {
        @NotNull(message = "카테고리명은 필수입니다")
        private String categoryName;

        private int totalRecommendedOrder;
        private String aiMessage;

        @NotEmpty(message = "상품 예측 목록은 비어있을 수 없습니다")
        @Valid
        private List<ProductPrediction> products;
    }

    @Getter
    @NoArgsConstructor
    public static class ProductPrediction {
        @NotNull(message = "PLU 코드는 필수입니다")
        private String pluCode;

        private int predictedSales;
        private int recommendedOrder;
        private Double confidenceScore;
    }
}
