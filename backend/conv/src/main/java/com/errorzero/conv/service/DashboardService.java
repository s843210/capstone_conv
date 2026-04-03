package com.errorzero.conv.service;

import com.errorzero.conv.domain.Product;
import com.errorzero.conv.dto.DashboardResponseDto.*;
import com.errorzero.conv.repository.AiPredictionRepository;
import com.errorzero.conv.repository.ProductRepository;
import com.errorzero.conv.util.StockCalculator;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class DashboardService {

    private static final int LOW_STOCK_THRESHOLD = 10;
    private static final int LOW_STOCK_DISPLAY_LIMIT = 5;

    private final ProductRepository productRepository;
    private final AiPredictionRepository aiPredictionRepository;

    public MainDashboard getDashboardData() {
        long totalItems = productRepository.countActiveProducts();
        long lowStockItems = productRepository.countLowStockProducts(LOW_STOCK_THRESHOLD);
        long normalItems = totalItems - lowStockItems;

        List<InventoryStat> inventoryStats = buildInventoryStats();
        List<OrderRecommendation> recommendations = buildOrderRecommendations();
        List<Insight> insights = buildInsights();

        return new MainDashboard(totalItems, normalItems, lowStockItems, inventoryStats, recommendations, insights);
    }

    /**
     * 재고 현황: 재고가 적은 상위 5개 품목 통계
     */
    private List<InventoryStat> buildInventoryStats() {
        Pageable pageable = PageRequest.of(0, LOW_STOCK_DISPLAY_LIMIT);
        List<Product> products = productRepository
                .findAllByIsActiveTrueAndCurrentStockLessThanOrderByCurrentStockAsc(LOW_STOCK_THRESHOLD, pageable);

        return products.stream()
                .map(p -> new InventoryStat(
                        p.getName(),
                        p.getCurrentStock(),
                        StockCalculator.calculateRecommendedStock(p.getCurrentStock())
                ))
                .collect(Collectors.toList());
    }

    /**
     * AI 발주 추천 (Mock Data)
     * TODO: FastAPI 구현 후 aiPredictionRepository.findAllByTargetDate(LocalDate.now())로 교체
     */
    private List<OrderRecommendation> buildOrderRecommendations() {
        return List.of(
                new OrderRecommendation("15000001", "참치마요 삼각김밥", 2, 15, "오후 3시 IT 학생들 전공 수업 직후 간식 수요 급증 예상"),
                new OrderRecommendation("15000002", "제육볶음 도시락", 4, 10, "오늘 야간 IT 학생들 야작 수요 20% 증가 패턴")
        );
    }

    /**
     * 오늘의 인사이트 (Mock Data)
     * TODO: FastAPI 구현 후 AI 분석 기반으로 동적 생성으로 교체
     */
    private List<Insight> buildInsights() {
        return List.of(
                new Insight("수요 급증", "오늘 저녁 도시락 수요 40% 증가 예상", ""),
                new Insight("품절주의", "생수 500ml 2시간 내 품절 위험", ""),
                new Insight("발주조정", "내일 비 예보, 우산 발주량 +20개 추천", ""),
                new Insight("수요증가", "주말 대학기 축제로 주류 수요 증가 진단", "")
        );
    }
}
