import { useState, useEffect, useMemo, useCallback } from "react";
import { fetchDashboard } from "../api/api";

const INSIGHT_STYLE_MAP = {
  "수요 급증": { typeClass: "alert", icon: "📈" },
  "품절주의": { typeClass: "warn", icon: "⚠️" },
  "발주조정": { typeClass: "info", icon: "📦" },
  "수요증가": { typeClass: "success", icon: "📊" },
};

const DEFAULT_INSIGHT_STYLE = { typeClass: "info", icon: "💡" };

/**
 * 대시보드 데이터 패칭 훅
 * - loading / error 상태 관리
 * - 원시 데이터를 UI 형태로 변환 (useMemo 적용)
 */
export function useDashboardData() {
  const [raw, setRaw] = useState({
    inventoryStats: [],
    recommendations: [],
    insights: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refreshDashboard = useCallback(async ({ showLoading = false } = {}) => {
    if (showLoading) {
      setLoading(true);
    }
    setError(null);

    try {
      const data = await fetchDashboard();
      setRaw(data);
      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshDashboard({ showLoading: true }).catch(() => {});
  }, [refreshDashboard]);

  /** 재고 현황 목록 (차트용) */
  const inventoryList = useMemo(
    () =>
      raw.inventoryStats.map((i) => ({
        name: i.itemName,
        stock: i.currentStock,
        target: i.recommendedStock,
        salesQty: i.salesQty || 0,
      })),
    [raw.inventoryStats],
  );

  /** AI 발주 추천 목록 */
  const orderList = useMemo(
    () =>
      raw.recommendations.map((r) => ({
        name: r.productName,
        category: r.category || "기타/미분류",
        current: r.currentStock,
        predicted: r.predictedSales,
        recommended: r.recommendedOrderQuantity,
        reason: r.aiReason,
      })),
    [raw.recommendations],
  );

  /** 오늘의 인사이트 목록 */
  const insights = useMemo(
    () =>
      raw.insights.map((insight) => {
        const style = INSIGHT_STYLE_MAP[insight.type] || DEFAULT_INSIGHT_STYLE;
        return {
          type: style.typeClass,
          icon: style.icon,
          title: insight.title,
          desc: insight.description || insight.type,
        };
      }),
    [raw.insights],
  );

  /** 백엔드에서 받아온 전체 DB 기준 통계 */
  const totalItems = raw.totalItems || 0;
  const normalItems = raw.normalItems || 0;
  const lowStockItems = raw.lowStockItems || 0;

  return {
    loading,
    error,
    inventoryList,
    orderList,
    insights,
    totalItems,
    normalItems,
    lowStockItems,
    refreshDashboard,
  };
}
