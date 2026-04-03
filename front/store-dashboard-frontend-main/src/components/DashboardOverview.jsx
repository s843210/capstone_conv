import InventoryChart from "./InventoryChart";
import OrderRecommendation from "./OrderRecommendation";
import InsightPanel from "./InsightPanel";

function DashboardOverview({
  inventoryList,
  totalItems,
  normalItems,
  lowStockItems,
  orderList,
  insights,
  onNavigateInventory,
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
    </section>
  );
}

export default DashboardOverview;
