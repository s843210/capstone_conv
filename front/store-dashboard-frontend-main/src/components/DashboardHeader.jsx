function DashboardHeader() {
  const now = new Date();
  const dateLabel = now.toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    weekday: "short",
  });

  return (
    <header className="top-header dashboard-header">
      <div>
        <h1>운영 대시보드</h1>
        <p>재고, 수요 예측, 발주 추천 정보를 한눈에 확인합니다.</p>
      </div>

      <div className="header-right">
        <span className="header-chip">{dateLabel}</span>
        <span className="admin-chip">관리자</span>
        <button className="icon-btn" type="button" aria-label="알림">🔔</button>
      </div>
    </header>
  );
}

export default DashboardHeader;
