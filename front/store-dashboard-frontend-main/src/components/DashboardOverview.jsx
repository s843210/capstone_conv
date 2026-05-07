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
  onNavigateStudentRequests,
}) {
  return (
    <section className="content-grid">
      <InventoryChart
        inventoryList={inventoryList}
        totalItems={totalItems}
        normalItems={normalItems}
        lowStockItems={lowStockItems}
        onNavigateInventory={onNavigateInventory}
      />
      <OrderRecommendation orderList={orderList} />
      <InsightPanel insights={insights} />
      <StudentRequestPanel
        limit={15}
        subtitle="최근 15개 자동 갱신"
        onViewAll={onNavigateStudentRequests}
      />
    </section>
  );
}

export default DashboardOverview;
