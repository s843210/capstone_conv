package com.errorzero.conv.service;

import com.errorzero.conv.domain.AiPrediction;
import com.errorzero.conv.domain.Product;
import com.errorzero.conv.dto.AiPredictionRequestDto;
import com.errorzero.conv.repository.AiPredictionRepository;
import com.errorzero.conv.repository.ProductRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * AI 예측 데이터를 수신·저장하는 서비스.
 * FastAPI에서 전달받은 예측 데이터를 Product와 매핑하여 DB에 저장합니다.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AiPredictionService {

    private final AiPredictionRepository aiPredictionRepository;
    private final ProductRepository productRepository;

    /**
     * FastAPI에서 받은 예측 데이터를 저장합니다.
     * - 현재 재고(product 테이블)에 없는 상품은 무시합니다 (과거 데이터일 수 있으므로).
     * - isActive가 false인 상품도 무시합니다.
     *
     * @param requestDto 예측 데이터 DTO
     * @return 실제 저장된 예측 건수
     */
    @Transactional
    public int savePredictions(AiPredictionRequestDto requestDto) {
        if (requestDto.getCategories() == null || requestDto.getCategories().isEmpty()) {
            return 0;
        }

        List<AiPrediction> newPredictions = new ArrayList<>();
        Map<String, Product> activeProductByPluCode = findActiveProductMap(requestDto.getCategories());
        Map<Long, AiPrediction> existingPredictionByProductId = findExistingPredictionMap(
                requestDto.getTargetDate(),
                activeProductByPluCode.values()
        );

        Set<Long> upsertedProductIds = new HashSet<>();
        int skippedCount = 0;

        for (AiPredictionRequestDto.CategoryPrediction category : requestDto.getCategories()) {
            if (category == null || category.getProducts() == null) {
                continue;
            }

            for (AiPredictionRequestDto.ProductPrediction productPrediction : category.getProducts()) {
                if (productPrediction == null) {
                    continue;
                }

                Product product = activeProductByPluCode.get(productPrediction.getPluCode());

                // 현재 재고에 없거나 비활성 상품이면 skip
                if (product == null) {
                    skippedCount++;
                    log.info("상품 skip (미존재 또는 비활성): pluCode={}", productPrediction.getPluCode());
                    continue;
                }

                AiPrediction prediction = existingPredictionByProductId.get(product.getId());
                if (prediction == null) {
                    prediction = AiPrediction.builder()
                            .product(product)
                            .targetDate(requestDto.getTargetDate())
                            .predictedSales(productPrediction.getPredictedSales())
                            .recommendedOrder(productPrediction.getRecommendedOrder())
                            .confidenceScore(productPrediction.getConfidenceScore())
                            .aiInsight(category.getAiMessage())
                            .build();
                    newPredictions.add(prediction);
                    existingPredictionByProductId.put(product.getId(), prediction);
                }

                prediction.updatePrediction(
                        productPrediction.getPredictedSales(),
                        productPrediction.getRecommendedOrder(),
                        productPrediction.getConfidenceScore(),
                        category.getAiMessage()
                );

                upsertedProductIds.add(product.getId());
            }
        }

        if (!newPredictions.isEmpty()) {
            aiPredictionRepository.saveAll(newPredictions);
        }

        int insertedCount = newPredictions.size();
        int upsertedCount = upsertedProductIds.size();
        int updatedCount = Math.max(upsertedCount - insertedCount, 0);

        log.info(
                "AI 예측 저장 완료: 신규={}건, 갱신={}건, 무시={}건, 대상일자={}",
                insertedCount,
                updatedCount,
                skippedCount,
                requestDto.getTargetDate()
        );

        return upsertedCount;
    }

    private Map<String, Product> findActiveProductMap(List<AiPredictionRequestDto.CategoryPrediction> categories) {
        if (categories == null || categories.isEmpty()) {
            return Map.of();
        }

        Set<String> pluCodes = new HashSet<>();

        for (AiPredictionRequestDto.CategoryPrediction category : categories) {
            if (category == null || category.getProducts() == null) {
                continue;
            }

            for (AiPredictionRequestDto.ProductPrediction productPrediction : category.getProducts()) {
                if (productPrediction == null || productPrediction.getPluCode() == null) {
                    continue;
                }
                pluCodes.add(productPrediction.getPluCode());
            }
        }

        if (pluCodes.isEmpty()) {
            return Map.of();
        }

        return productRepository.findAllByPluCodeInAndIsActiveTrue(pluCodes)
                .stream()
                .collect(Collectors.toMap(Product::getPluCode, Function.identity(), (left, right) -> left));
    }

    private Map<Long, AiPrediction> findExistingPredictionMap(
            java.time.LocalDate targetDate,
            Collection<Product> products
    ) {
        if (products.isEmpty()) {
            return new HashMap<>();
        }

        return aiPredictionRepository.findAllByTargetDateAndProductIn(targetDate, products)
                .stream()
                .collect(Collectors.toMap(
                        prediction -> prediction.getProduct().getId(),
                        Function.identity(),
                        (left, right) -> left
                ));
    }
}
