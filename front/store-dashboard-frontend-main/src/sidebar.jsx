import "./Sidebar.css";

function Sidebar() {
  const menus = [
    "대시보드",
    "재고 관리",
    "발주 추천",
    "매출 분석",
    "공지 관리",
    "설정",
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-top">
        <h2 className="sidebar-logo">StoreDash</h2>
        <p className="sidebar-subtitle">Campus Store Admin</p>
      </div>

      <nav className="sidebar-menu">
        {menus.map((menu, index) => (
          <button
            key={menu}
            className={`sidebar-item ${index === 0 ? "active" : ""}`}
          >
            {menu}
          </button>
        ))}
      </nav>

      <div className="sidebar-bottom">
        <p>관리자님, 환영합니다.</p>
      </div>
    </aside>
  );
}

export default Sidebar;