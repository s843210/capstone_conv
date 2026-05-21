package com.errorzero.conv.service;

import com.errorzero.conv.domain.AiPrediction;
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

import java.time.LocalDate;
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

    private List<OrderRecommendation> buildOrderRecommendations() {
        LocalDate targetDate = aiPredictionRepository.findLatestRecommendedTargetDate().orElse(null);
        if (targetDate == null) {
            return List.of();
        }

        return aiPredictionRepository
                .findAllByTargetDateAndRecommendedOrderGreaterThanOrderByRecommendedOrderDesc(targetDate, 1)
                .stream()
                .map(this::toOrderRecommendation)
                .collect(Collectors.toList());
    }

    private OrderRecommendation toOrderRecommendation(AiPrediction prediction) {
        Product product = prediction.getProduct();
        return new OrderRecommendation(
                product.getPluCode(),
                product.getName(),
                product.getCurrentStock(),
                prediction.getRecommendedOrder(),
                "AI target_date=" + prediction.getTargetDate()
        );
    }

    private List<Insight> buildInsights() {
        return List.of();
    }
}
