package com.errorzero.conv.service;

import com.errorzero.conv.domain.Product;
import com.errorzero.conv.dto.DashboardResponseDto.*;
import com.errorzero.conv.repository.AiPredictionRepository;
import com.errorzero.conv.repository.ProductRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class DashboardService {

    private final ProductRepository productRepository;
    private final AiPredictionRepository aiPredictionRepository;

    public MainDashboard getDashboardData() {
        
        // 1. 재고 현황 (품목별 통계 - 예시로 재고가 적은 상위 5개 품목)
        List<Product> products = productRepository.findAllByIsActiveTrue();
        
        List<InventoryStat> inventoryStats = products.stream()
                .filter(p -> p.getCurrentStock() < 10) // 재고가 적은 품목 샘플링
                .limit(5)
                .map(p -> {
                    int recommended = p.getCurrentStock() == 0 ? 20 : (int)(p.getCurrentStock() * 1.5);
                    return new InventoryStat(p.getName(), p.getCurrentStock(), recommended);
                })
                .collect(Collectors.toList());

        // 2. AI 발주 추천 (Mock Data - 향후 aiPredictionRepository에서 조회)
        List<OrderRecommendation> recommendations = List.of(
                new OrderRecommendation("15000001", "참치마요 삼각김밥", 2, 15, "오후 3시 IT 학생들 전공 수업 직후 간식 수요 급증 예상"),
                new OrderRecommendation("15000002", "제육볶음 도시락", 4, 10, "오늘 야간 IT 학생들 야작 수요 20% 증가 패턴")
        );

        // 3. 오늘의 인사이트 (Mock Data - 향후 AI 분석 기반으로 교체)
        List<Insight> insights = List.of(
                new Insight("수요 급증", "오늘 저녁 도시락 수요 40% 증가 예상", ""),
                new Insight("품절주의", "생수 500ml 2시간 내 품절 위험", ""),
                new Insight("발주조정", "내일 비 예보, 우산 발주량 +20개 추천", ""),
                new Insight("수요증가", "주말 대학기 축제로 주류 수요 증가 진단", "")
        );

        return new MainDashboard(inventoryStats, recommendations, insights);
    }
}
