import { useState } from "react";
import "./DashboardPage.css";
import Sidebar from "./components/Sidebar";
import DashboardHeader from "./components/DashboardHeader";
import DashboardOverview from "./components/DashboardOverview";
import InventoryPanel from "./components/InventoryPanel";
import AcademicContextPanel from "./components/AcademicContextPanel";
import AiRunPanel from "./components/AiRunPanel";
import InventoryUploadPanel from "./components/InventoryUploadPanel";
import ProductMasterUploadPanel from "./components/ProductMasterUploadPanel";
import SalesUploadPanel from "./components/SalesUploadPanel";
import StudentRequestPage from "./components/StudentRequestPage";
import WeatherContextPanel from "./components/WeatherContextPanel";
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
            onNavigateStudentRequests={() => setActivePage("studentRequests")}
          />
        )}

        {activePage === "inventory" && (
          <InventoryPanel isActive={activePage === "inventory"} />
        )}

        {activePage === "studentRequests" && <StudentRequestPage />}

        {activePage === "settings" && (
          <div className="settings-stack">
            <SalesUploadPanel />
            <InventoryUploadPanel />
            <WeatherContextPanel />
            <AiRunPanel />
            <ProductMasterUploadPanel />
            <AcademicContextPanel />
          </div>
        )}
      </main>
    </div>
  );
}

export default DashboardPage;
