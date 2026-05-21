package com.errorzero.conv.service;

import com.errorzero.conv.domain.AiPrediction;
import com.errorzero.conv.domain.Product;
import com.errorzero.conv.dto.DashboardResponseDto.*;
import com.errorzero.conv.repository.AiPredictionRepository;
import com.errorzero.conv.repository.DailySalesRepository;
import com.errorzero.conv.util.StockCalculator;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class DashboardService {

    private static final int TOP_SALES_DISPLAY_LIMIT = 10;
    private static final double STOCK_NORMAL_LOWER_RATE = 0.75;
    private static final double STOCK_NORMAL_UPPER_RATE = 1.25;

    private final AiPredictionRepository aiPredictionRepository;
    private final DailySalesRepository dailySalesRepository;

    public MainDashboard getDashboardData() {
        StockHealthSummary stockHealth = buildStockHealthSummary();

        List<InventoryStat> inventoryStats = buildInventoryStats();
        List<OrderRecommendation> recommendations = buildOrderRecommendations();
        List<Insight> insights = buildInsights();

        return new MainDashboard(
                stockHealth.totalItems(),
                stockHealth.normalItems(),
                stockHealth.lowStockItems(),
                inventoryStats,
                recommendations,
                insights
        );
    }

    private StockHealthSummary buildStockHealthSummary() {
        LocalDate targetDate = aiPredictionRepository.findLatestTargetDate().orElse(null);
        if (targetDate == null) {
            return new StockHealthSummary(0, 0, 0);
        }

        long totalItems = 0;
        long normalItems = 0;
        long lowStockItems = 0;

        for (AiPrediction prediction : aiPredictionRepository.findAllByTargetDate(targetDate)) {
            int predictedSales = safeInt(prediction.getPredictedSales());
            if (predictedSales <= 0 || !isActiveProduct(prediction.getProduct())) {
                continue;
            }

            int currentStock = safeInt(prediction.getProduct().getCurrentStock());
            int lowerBound = (int) Math.ceil(predictedSales * STOCK_NORMAL_LOWER_RATE);
            int upperBound = (int) Math.floor(predictedSales * STOCK_NORMAL_UPPER_RATE);

            totalItems++;
            if (currentStock < lowerBound) {
                lowStockItems++;
            }
            if (currentStock >= lowerBound && currentStock <= upperBound) {
                normalItems++;
            }
        }

        return new StockHealthSummary(totalItems, normalItems, lowStockItems);
    }

    private List<InventoryStat> buildInventoryStats() {
        return dailySalesRepository.findTopSellingProductsByLatestUpload(TOP_SALES_DISPLAY_LIMIT).stream()
                .map(product -> new InventoryStat(
                        product.getName(),
                        safeInt(product.getCurrentStock()),
                        StockCalculator.calculateRecommendedStock(safeInt(product.getCurrentStock())),
                        safeInt(product.getSalesQty())
                ))
                .collect(Collectors.toList());
    }

    private int safeInt(Integer value) {
        return value == null ? 0 : value;
    }

    private boolean isActiveProduct(Product product) {
        return product != null && Boolean.TRUE.equals(product.getIsActive());
    }

    private List<OrderRecommendation> buildOrderRecommendations() {
        LocalDate targetDate = aiPredictionRepository.findLatestTargetDate().orElse(null);
        if (targetDate == null) {
            return List.of();
        }

        return aiPredictionRepository
                .findAllByTargetDate(targetDate)
                .stream()
                .filter(prediction -> isActiveProduct(prediction.getProduct()))
                .filter(prediction -> calculateRecommendedOrder(prediction) > 0)
                .sorted((left, right) -> Integer.compare(
                        calculateRecommendedOrder(right),
                        calculateRecommendedOrder(left)
                ))
                .map(this::toOrderRecommendation)
                .collect(Collectors.toList());
    }

    private int calculateRecommendedOrder(AiPrediction prediction) {
        if (prediction == null || prediction.getProduct() == null) {
            return 0;
        }
        return Math.max(safeInt(prediction.getPredictedSales()) - safeInt(prediction.getProduct().getCurrentStock()), 0);
    }

    private OrderRecommendation toOrderRecommendation(AiPrediction prediction) {
        Product product = prediction.getProduct();
        return new OrderRecommendation(
                product.getPluCode(),
                product.getName(),
                product.getCategory(),
                product.getCurrentStock(),
                prediction.getPredictedSales(),
                calculateRecommendedOrder(prediction),
                "AI target_date=" + prediction.getTargetDate()
        );
    }

    private List<Insight> buildInsights() {
        return List.of();
    }

    private record StockHealthSummary(long totalItems, long normalItems, long lowStockItems) {
    }
}
