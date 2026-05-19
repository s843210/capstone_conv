function OrderRecommendation({ orderList }) {
  const rows = orderList.slice(0, 10);

  return (
    <article className="panel order-panel">
      <div className="panel-header with-icon">
        <h2>
          <span className="head-icon purple" aria-hidden="true">📊</span>
          우선 발주 추천 상품 TOP10
        </h2>
        <button className="mini-action" type="button">전체보기</button>
      </div>

      <div className="table-wrap">
        <div className="thead row">
          <span>순위</span>
          <span>상품명</span>
          <span>추천 발주량</span>
        </div>

        {rows.map((item, idx) => (
          <div className="row" key={`${item.name}-${idx}`}>
            <span className="rank">{idx + 1}</span>
            <span className="prod">{item.name}</span>
            <span className="qty-badge">{item.recommended}개</span>
          </div>
        ))}
      </div>
    </article>
  );
}

export default OrderRecommendation;
