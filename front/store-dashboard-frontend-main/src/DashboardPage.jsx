import { useState } from "react";
import "./DashboardPage.css";
import Sidebar from "./components/Sidebar";
import DashboardHeader from "./components/DashboardHeader";
import DashboardOverview from "./components/DashboardOverview";
import InventoryPanel from "./components/InventoryPanel";
import { useDashboardData } from "./hooks/useDashboardData";

function DashboardPage({ onLogout }) {
  const [activePage, setActivePage] = useState("dashboard");
  const { loading, error, inventoryList, orderList, insights, totalItems, normalItems, lowStockItems } =
    useDashboardData();

  return (
    <div className="dashboard-layout">
      <Sidebar
        activePage={activePage}
        onPageChange={setActivePage}
        onLogout={onLogout}
      />

      <main className="dashboard-main">
        <DashboardHeader />

        {loading && (
          <div className="loading-state">데이터를 불러오는 중...</div>
        )}

        {error && (
          <div className="error-state">
            ⚠️ 데이터를 불러오지 못했습니다: {error}
          </div>
        )}

        {!loading && !error && activePage === "dashboard" && (
          <DashboardOverview
            inventoryList={inventoryList}
            totalItems={totalItems}
            normalItems={normalItems}
            lowStockItems={lowStockItems}
            orderList={orderList}
            insights={insights}
            onNavigateInventory={() => setActivePage("inventory")}
          />
        )}

        {activePage === "inventory" && (
          <InventoryPanel isActive={activePage === "inventory"} />
        )}

        {activePage === "forecast" && (
          <div className="panel placeholder-panel">
            <div className="panel-header">
              <div className="panel-title">
                <span className="panel-icon">📈</span>
                <h2>수요 예측</h2>
              </div>
            </div>
            <p className="placeholder-text">수요 예측 기능 준비 중입니다.</p>
          </div>
        )}

        {activePage === "order" && (
          <div className="panel placeholder-panel">
            <div className="panel-header">
              <div className="panel-title">
                <span className="panel-icon">🛒</span>
                <h2>발주 추천</h2>
              </div>
            </div>
            <p className="placeholder-text">발주 추천 기능 준비 중입니다.</p>
          </div>
        )}

        {activePage === "settings" && (
          <div className="panel placeholder-panel">
            <div className="panel-header">
              <div className="panel-title">
                <span className="panel-icon">⚙️</span>
                <h2>설정</h2>
              </div>
            </div>
            <p className="placeholder-text">설정 기능 준비 중입니다.</p>
          </div>
        )}
      </main>
    </div>
  );
}

export default DashboardPage;
