import "../DashboardPage.css";

const MENU_ITEMS = [
  { key: "dashboard", label: "대시보드" },
  { key: "inventory", label: "재고 관리" },
  { key: "order", label: "발주 추천" },
  { key: "studentRequests", label: "학생 요청 현황" },
  { key: "suggestions", label: "건의사항" },
  { key: "settings", label: "설정" },
];

function Sidebar({ activePage, isOpen = false, onClose, onPageChange, onLogout }) {
  return (
    <aside className={`sidebar ${isOpen ? "open" : ""}`} aria-label="관리자 메뉴">
      <div className="sidebar-content">
        <div className="sidebar-top">
          <div className="logo-area brand-area">
            <h2 className="logo">COOPSKET</h2>
            <p className="sidebar-subtitle">IT Convenience Store</p>
            <button className="sidebar-close-btn" type="button" aria-label="메뉴 닫기" onClick={onClose}>
              ×
            </button>
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

        <div className="sidebar-bottom-card">
          <p>AI 예측과 재고 지표를 기반으로 운영 판단을 빠르게 지원합니다.</p>
        </div>

        <button className="logout-btn" onClick={onLogout}>
          로그아웃
        </button>
      </div>

      <div className="sidebar-peek" aria-hidden="true">
        <span className="sidebar-peek-mark">C</span>
        <span className="sidebar-peek-text">MENU</span>
      </div>
    </aside>
  );
}

export default Sidebar;
