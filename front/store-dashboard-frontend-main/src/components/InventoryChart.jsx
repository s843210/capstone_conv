import { useMemo } from "react";

function InventoryChart({
  inventoryList,
  totalItems,
  normalItems,
  lowStockItems,
  onNavigateInventory,
}) {
  const isNavigable = typeof onNavigateInventory === "function";

  const handleKeyDown = (event) => {
    if (!isNavigable) return;

    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onNavigateInventory();
    }
  };

  /** 재고 부족 → 정상 순으로 정렬, 최대 8개만 표시 */
  const displayItems = useMemo(() => {
    return [...inventoryList]
      .sort((a, b) => {
        const ratioA = a.target > 0 ? a.stock / a.target : 1;
        const ratioB = b.target > 0 ? b.stock / b.target : 1;
        return ratioA - ratioB;
      })
      .slice(0, 8);
  }, [inventoryList]);

  return (
    <div
      className={`panel ${isNavigable ? "panel-clickable" : ""}`}
      onClick={isNavigable ? onNavigateInventory : undefined}
      onKeyDown={handleKeyDown}
      role={isNavigable ? "button" : undefined}
      tabIndex={isNavigable ? 0 : undefined}
      aria-label={isNavigable ? "재고 관리 페이지로 이동" : undefined}
    >
      <div className="panel-header">
        <div className="panel-title">
          <span className="panel-icon">📦</span>
          <h2>재고 현황</h2>
        </div>
        {lowStockItems > 0 && (
          <span className="badge danger">⚠️ 부족 {lowStockItems}건</span>
        )}
      </div>

      {isNavigable && (
        <p className="panel-link-hint">차트(그레이 바 포함) 클릭 시 재고 관리로 이동</p>
      )}

      {/* 요약 카드 */}
      <div className="inventory-summary">
        <div className="summary-stat">
          <span className="summary-stat-value">{totalItems}</span>
          <span className="summary-stat-label">전체 품목</span>
        </div>
        <div className="summary-stat">
          <span className="summary-stat-value text-green">{normalItems}</span>
          <span className="summary-stat-label">정상</span>
        </div>
        <div className="summary-stat">
          <span className="summary-stat-value text-red">{lowStockItems}</span>
          <span className="summary-stat-label">부족</span>
        </div>
      </div>

      {/* 상품별 재고 리스트 */}
      <div className="inventory-bars">
        {displayItems.map((item) => {
          const ratio = item.target > 0 ? Math.min((item.stock / item.target) * 100, 100) : 100;
          const isLow = item.stock < item.target;

          return (
            <div key={item.name} className="inventory-bar-row">
              <div className="inventory-bar-info">
                <span className="inventory-bar-name">{item.name}</span>
                <span className={`inventory-bar-count ${isLow ? "text-red" : "text-muted"}`}>
                  {item.stock} / {item.target}
                </span>
              </div>
              <div className="inventory-bar-track">
                <div
                  className={`inventory-bar-fill ${isLow ? "bar-red" : "bar-blue"}`}
                  style={{ width: `${Math.max(ratio, 0)}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default InventoryChart;
