function InsightPanel({ insights }) {
  const rows = insights.slice(0, 6);

  return (
    <article className="panel">
      <div className="panel-header with-icon">
        <h2>
          <span className="head-icon" aria-hidden="true">💭</span>
          건의사항
        </h2>
        <button className="mini-action primary" type="button">등록하기</button>
      </div>

      <div className="table-wrap small">
        <div className="thead row suggestion-head">
          <span>제목</span>
          <span>내용</span>
          <span>작성 시간</span>
        </div>

        {rows.map((item, idx) => (
          <div className="row suggestion-row" key={`${item.title}-${idx}`}>
            <span className="prod">{item.title}</span>
            <span className="preview">{item.desc}</span>
            <span>{idx === 0 ? "방금" : `${idx + 1}분 전`}</span>
          </div>
        ))}
      </div>
    </article>
  );
}

export default InsightPanel;
