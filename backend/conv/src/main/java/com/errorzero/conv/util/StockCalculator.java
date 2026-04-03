package com.errorzero.conv.util;

/**
 * 추천 재고량 계산 유틸리티.
 * DashboardService, InventoryService에서 동일 로직이 중복되어 추출.
 */
public final class StockCalculator {

    private static final int DEFAULT_RECOMMENDED_STOCK = 20;
    private static final double STOCK_MULTIPLIER = 1.5;

    private StockCalculator() {
        // 유틸리티 클래스 인스턴스화 방지
    }

    /**
     * 현재 재고를 기반으로 추천 재고량을 계산합니다.
     * 재고가 0이면 기본값(20), 그 외에는 현재 재고의 1.5배를 반환합니다.
     *
     * @param currentStock 현재 재고 수량
     * @return 추천 재고 수량
     */
    public static int calculateRecommendedStock(int currentStock) {
        if (currentStock == 0) {
            return DEFAULT_RECOMMENDED_STOCK;
        }
        return (int) (currentStock * STOCK_MULTIPLIER);
    }
}
