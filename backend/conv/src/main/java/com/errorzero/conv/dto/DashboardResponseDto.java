package com.errorzero.conv.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;

import java.util.List;

public class DashboardResponseDto {

    @Getter
    @Builder
    @AllArgsConstructor
    public static class MainDashboard {
        private final List<InventoryStat> inventoryStats;
        private final List<OrderRecommendation> recommendations;
        private final List<Insight> insights;
    }

    @Getter
    @Builder
    @AllArgsConstructor
    public static class InventoryStat {
        private final String itemName;
        private final int currentStock;
        private final int recommendedStock;
    }

    @Getter
    @Builder
    @AllArgsConstructor
    public static class OrderRecommendation {
        private final String pluCode;
        private final String productName;
        private final int currentStock;
        private final int recommendedOrderQuantity;
        private final String aiReason;
    }

    @Getter
    @Builder
    @AllArgsConstructor
    public static class Insight {
        private final String type; // e.g. "수요 급증", "품절주의"
        private final String title;
        private final String description;
    }
}
