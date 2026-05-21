import InventoryChart from "./InventoryChart";
import OrderRecommendation from "./OrderRecommendation";
import InsightPanel from "./InsightPanel";
import StudentRequestPanel from "./StudentRequestPanel";

function DashboardOverview({
  inventoryList,
  totalItems,
  normalItems,
  lowStockItems,
  orderList,
  insights,
  onNavigateInventory,
  onNavigateOrder,
  onNavigateStudentRequests,
  onNavigateSuggestions,
}) {
  const now = new Date();
  const nowLabel = now.toLocaleString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <>
      <section className="content-grid dashboard-grid">
        <InventoryChart
          inventoryList={inventoryList}
          totalItems={totalItems}
          normalItems={normalItems}
          lowStockItems={lowStockItems}
          onNavigateInventory={onNavigateInventory}
        />

        <OrderRecommendation orderList={orderList} onViewAll={onNavigateOrder} />

        <StudentRequestPanel
          limit={15}
          subtitle="최근 15건 자동 갱신"
          onViewAll={onNavigateStudentRequests}
        />

        <InsightPanel insights={insights} onViewAll={onNavigateSuggestions} />
      </section>

      <section className="status-bar">
        <div className="status-cell">
          <span>서비스 상태</span>
          <strong>정상 운영 중</strong>
        </div>
        <div className="status-cell">
          <span>최근 데이터 반영</span>
          <strong>{nowLabel}</strong>
        </div>
        <div className="status-cell">
          <span>부족 재고 품목</span>
          <strong>{lowStockItems}개</strong>
        </div>
        <div className="status-cell">
          <span>추천 발주 품목</span>
          <strong>{orderList.length}개</strong>
        </div>
        <div className="status-cell">
          <span>정상 품목 비율</span>
          <strong>
            {totalItems > 0 ? Math.round((normalItems / totalItems) * 100) : 0}%
          </strong>
        </div>
      </section>
    </>
  );
}

export default DashboardOverview;
