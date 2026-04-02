import { useState } from "react";
import "./DashboardPage.css";
import {
  Chart as ChartJs,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
  LineController,
} from "chart.js";
import { Bar } from "react-chartjs-2";

ChartJs.register(
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  LineController,
  Tooltip,
  Legend,
);

function DashboardPage({ onLogout }) {
  const [activePage, setActivePage] = useState("dashboard");

  const inventoryList = [
    { name: "콜라", stock: 45, target: 20 },
    { name: "사이다", stock: 30, target: 20 },
    { name: "생수", stock: 80, target: 30 },
    { name: "삼각김밥", stock: 5, target: 20 },
    { name: "도시락", stock: 12, target: 15 },
    { name: "샌드위치", stock: 8, target: 10 },
    { name: "컵라면", stock: 50, target: 25 },
    { name: "과자", stock: 3, target: 20 },
  ];

  const forecastList = [
    { day: "월", actual: 200, predicted: 210 },
    { day: "화", actual: 180, predicted: 190 },
    { day: "수", actual: 400, predicted: 380 },
    { day: "목", actual: 300, predicted: 310 },
    { day: "금", actual: 500, predicted: 480 },
    { day: "토", actual: 600, predicted: 580 },
    { day: "일", actual: 420, predicted: 400 },
  ];

  const orderList = [
    {
      name: "참치마요 삼각김밥",
      current: 2,
      recommended: 15,
      reason: "오후 3시 IT학생들 간식 수요 급증 예상",
    },
    {
      name: "제육볶음 도시락",
      current: 4,
      recommended: 10,
      reason: "오늘 IT학생들 어착 수요 20% 증가 예정",
    },
  ];

  const insights = [
    {
      type: "alert",
      icon: "📈",
      title: "수요 급증",
      desc: "오늘 저녁 도시락 수요 40% 증가 예상",
    },
    {
      type: "warn",
      icon: "⚠️",
      title: "품절주의",
      desc: "생수 500ml 2시간 내 품절 위험",
    },
    {
      type: "info",
      icon: "📦",
      title: "발주조정",
      desc: "내일 비 예보, 우산 발주량 +20개 추천",
    },
    {
      type: "success",
      icon: "📊",
      title: "수요증가",
      desc: "주말 대학가 축제로 주류 수요 증가 전망",
    },
  ];

  const lowStockCount = inventoryList.filter((i) => i.stock < i.target).length;

  const inventoryChartData = {
    labels: inventoryList.map((i) => i.name),
    datasets: [
      {
        label: "현재 재고",
        data: inventoryList.map((i) => i.stock),
        backgroundColor: inventoryList.map((i) =>
          i.stock < i.target ? "#ef4444" : "#3b82f6",
        ),
        borderRadius: 6,
      },
    ],
  };

  const inventoryChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          afterBody: (ctx) => {
            const item = inventoryList[ctx[0].dataIndex];
            return `적정 재고선: ${item.target}`;
          },
        },
      },
    },
    scales: {
      y: { beginAtZero: true, grid: { color: "#f1f5f9" } },
      x: { grid: { display: false } },
    },
  };

  const forecastChartData = {
    labels: forecastList.map((i) => i.day),
    datasets: [
      {
        label: "실제",
        data: forecastList.map((i) => i.actual),
        backgroundColor: "#cbd5e1",
        borderRadius: 6,
      },
      {
        label: "예측",
        data: forecastList.map((i) => i.predicted),
        backgroundColor: "#3b82f6",
        borderRadius: 6,
      },
    ],
  };

  const forecastChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: "bottom",
        labels: { usePointStyle: true, pointStyle: "circle" },
      },
    },
    scales: {
      y: { beginAtZero: true, grid: { color: "#f1f5f9" } },
      x: { grid: { display: false } },
    },
  };

  return (
    <div className="dashboard-layout">
      <aside className="sidebar">
        <div className="sidebar-top">
          <div className="logo-area">
            <h2 className="logo">Smart Shelf</h2>
            <p className="sidebar-subtitle">Coopsket Admin(IT)</p>
          </div>
          <nav className="menu">
            <button
              className={`menu-item ${activePage === "dashboard" ? "active" : ""}`}
              onClick={() => setActivePage("dashboard")}
            >
              대시보드
            </button>
            <button
              className={`menu-item ${activePage === "inventory" ? "active" : ""}`}
              onClick={() => setActivePage("inventory")}
            >
              재고 관리
            </button>
            <button
              className={`menu-item ${activePage === "forecast" ? "active" : ""}`}
              onClick={() => setActivePage("forecast")}
            >
              수요 예측
            </button>
            <button
              className={`menu-item ${activePage === "order" ? "active" : ""}`}
              onClick={() => setActivePage("order")}
            >
              발주 추천
            </button>
            <button
              className={`menu-item ${activePage === "settings" ? "active" : ""}`}
              onClick={() => setActivePage("settings")}
            >
              설정
            </button>
          </nav>
        </div>
        <button className="logout-btn" onClick={onLogout}>
          로그아웃
        </button>
      </aside>

      <main className="dashboard-main">
        <header className="dashboard-header">
          <div>
            <h1>운영자 대시보드</h1>
            <p>재고, 수요 예측, 발주 추천 정보를 한눈에 확인합니다.</p>
          </div>
        </header>

        {/* 재고 관리 탭 */}
        {activePage === "inventory" && (
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">
                <span className="panel-icon">📦</span>
                <h2>재고 관리</h2>
              </div>
            </div>
            <ul className="item-list">
              {inventoryList.map((item) => (
                <li key={item.name}>
                  <div>
                    <strong>{item.name}</strong>
                    <p>
                      현재 재고 {item.stock}개 / 적정 재고 {item.target}개
                    </p>
                  </div>
                  <span
                    className={`badge ${item.stock < item.target ? "danger" : "normal"}`}
                  >
                    {item.stock < item.target ? "부족" : "정상"}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* 대시보드 탭 */}
        {activePage === "dashboard" && (
          <section className="content-grid">
            {/* 재고 현황 */}
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">
                  <span className="panel-icon">📦</span>
                  <h2>재고 현황</h2>
                </div>
                {lowStockCount > 0 && (
                  <span className="badge danger">
                    ⚠️ 부족 {lowStockCount}건
                  </span>
                )}
              </div>
              <div className="chart-box">
                <Bar
                  data={inventoryChartData}
                  options={inventoryChartOptions}
                />
              </div>
            </div>

            {/* AI 수요 예측 리포트 */}
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">
                  <span className="panel-icon">📈</span>
                  <h2>AI 예측 수요 리포트</h2>
                </div>
                <span className="accuracy-badge">AI 예측 정확도 ✅ 87.3%</span>
              </div>
              <div className="chart-box">
                <Bar data={forecastChartData} options={forecastChartOptions} />
              </div>
            </div>

            {/* AI 발주 추천 */}
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">
                  <span className="panel-icon">🛒</span>
                  <h2>AI 발주 추천</h2>
                </div>
              </div>
              <p className="panel-desc">곧 발주하면 품절을 막을 수 있어요</p>
              <div className="order-list">
                {orderList.map((item) => (
                  <div key={item.name} className="order-item">
                    <div className="order-top">
                      <strong>{item.name}</strong>
                      <span className="order-qty">
                        현재 {item.current} / {item.recommended}개 권장
                      </span>
                    </div>
                    <div className="progress-bar">
                      <div
                        className="progress-fill"
                        style={{
                          width: `${Math.min((item.current / item.recommended) * 100, 100)}%`,
                        }}
                      />
                    </div>
                    <p className="order-reason">⚡ {item.reason}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* 오늘의 인사이트 */}
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">
                  <span className="panel-icon">💡</span>
                  <h2>오늘의 인사이트</h2>
                </div>
              </div>
              <div className="insight-grid">
                {insights.map((item) => (
                  <div key={item.title} className={`insight-card ${item.type}`}>
                    <span className="insight-icon">{item.icon}</span>
                    <strong>{item.title}</strong>
                    <p>{item.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default DashboardPage;
