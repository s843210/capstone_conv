function InsightPanel({ insights }) {
  return (
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
  );
}

export default InsightPanel;
