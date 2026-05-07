import "../DashboardPage.css";

const MENU_ITEMS = [
  { key: "dashboard", label: "대시보드" },
  { key: "inventory", label: "재고 관리" },
  { key: "studentRequests", label: "학생 신청현황" },
  { key: "settings", label: "설정" },
];

function Sidebar({ activePage, onPageChange, onLogout }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-top">
        <div className="logo-area">
          <h2 className="logo">Smart Shelf</h2>
          <p className="sidebar-subtitle">Coopsket Admin(IT)</p>
        </div>
        <nav className="menu">
          {MENU_ITEMS.map((item) => (
            <button
              key={item.key}
              className={`menu-item ${activePage === item.key ? "active" : ""}`}
              onClick={() => onPageChange(item.key)}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </div>
      <button className="logout-btn" onClick={onLogout}>
        로그아웃
      </button>
    </aside>
  );
}

export default Sidebar;
