function OrderRecommendation({ orderList }) {
  return (
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
  );
}

export default OrderRecommendation;
