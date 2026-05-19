import { useMemo } from "react";

function InventoryChart({
  inventoryList,
  totalItems,
  normalItems,
  lowStockItems,
  onNavigateInventory,
}) {
  const sortedItems = useMemo(
    () =>
      [...inventoryList]
        .sort((a, b) => {
          const ratioA = a.target > 0 ? a.stock / a.target : 1;
          const ratioB = b.target > 0 ? b.stock / b.target : 1;
          return ratioA - ratioB;
        })
        .slice(0, 6),
    [inventoryList],
  );

  const categoryRows = useMemo(() => {
    const groups = new Map();

    sortedItems.forEach((item) => {
      const key = item.name?.includes("음료")
        ? "음료"
        : item.name?.includes("디저트") || item.name?.includes("빵")
          ? "디저트"
          : item.name?.includes("즉석") || item.name?.includes("간편")
            ? "간편식"
            : "기타";

      const prev = groups.get(key) || { stock: 0, target: 0 };
      groups.set(key, {
        stock: prev.stock + Number(item.stock || 0),
        target: prev.target + Number(item.target || 0),
      });
    });

    return Array.from(groups.entries())
      .map(([label, value]) => {
        const ratio = value.target > 0 ? Math.min((value.stock / value.target) * 100, 100) : 100;
        return { label, ratio: Math.max(0, ratio) };
      })
      .slice(0, 4);
  }, [sortedItems]);

  return (
    <section className="panel inventory-panel">
      <div className="panel-header with-icon">
        <h2>
          <span className="head-icon" aria-hidden="true">📦</span>
          재고 현황
        </h2>
      </div>

      <div className="stat-grid">
        <article className="stat-card">
          <span className="stat-label">전체 품목</span>
          <span className="stat-value">{totalItems}</span>
          <em>개</em>
        </article>
        <article className="stat-card">
          <span className="stat-label">정상 품목</span>
          <span className="stat-value">{normalItems}</span>
          <em>개</em>
        </article>
        <article className="stat-card">
          <span className="stat-label">부족 품목</span>
          <span className="stat-value">{lowStockItems}</span>
          <em>개</em>
        </article>
        <article className="stat-card">
          <span className="stat-label">안정 비율</span>
          <span className="stat-value">
            {totalItems > 0 ? Math.round((normalItems / totalItems) * 100) : 0}
          </span>
          <em>%</em>
        </article>
      </div>

      <div className="inventory-bottom">
        <div className="low-stock-box">
          <span>재고 부족 경고</span>
          <strong>{lowStockItems}</strong>
          <em>건</em>
        </div>

        <div className="category-ratio">
          <p className="category-ratio-title">카테고리 충족률</p>
          {categoryRows.map((row, index) => {
            const fillClass = ["blue", "purple", "green", "orange"][index % 4];
            return (
              <div key={row.label} className="ratio-row">
                <div className="ratio-top">
                  <span>{row.label}</span>
                  <strong>{Math.round(row.ratio)}%</strong>
                </div>
                <div className="ratio-bar">
                  <div className={`ratio-fill ${fillClass}`} style={{ width: `${row.ratio}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="table-wrap" style={{ marginTop: "10px" }}>
        <div className="row thead">
          <span>순위</span>
          <span>상품명</span>
          <span>재고/기준</span>
        </div>
        {sortedItems.map((item, idx) => (
          <div className="row" key={`${item.name}-${idx}`}>
            <span className="rank">#{idx + 1}</span>
            <span className="prod">{item.name}</span>
            <span className="qty-badge">{item.stock}/{item.target}</span>
          </div>
        ))}
      </div>

      <div style={{ marginTop: "10px" }}>
        <button className="mini-action primary" type="button" onClick={onNavigateInventory}>
          재고 관리로 이동
        </button>
      </div>
    </section>
  );
}

export default InventoryChart;
