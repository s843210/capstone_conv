import { useState } from "react";
import { runAiPrediction } from "../api/api";

function AiRunPanel() {
  const [targetDate, setTargetDate] = useState("");
  const [onlyPositiveRecommendations, setOnlyPositiveRecommendations] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setResult(null);
    setLoading(true);

    try {
      const response = await runAiPrediction({
        targetDate,
        onlyPositiveRecommendations,
      });
      setResult(response);
    } catch (err) {
      setError(err.message || "AI 예측 실행 중 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">
          <span className="panel-icon">AI</span>
          <h2>AI 예측 실행</h2>
        </div>
      </div>

      <p className="panel-desc">
        FastAPI monthly_v2 예측을 실행하고 결과를 <code>ai_prediction</code>에 저장합니다.
      </p>

      <form className="sales-upload-form" onSubmit={handleSubmit}>
        <label className="sales-upload-field">
          <span>예측 대상일 (선택)</span>
          <input
            type="date"
            value={targetDate}
            onChange={(event) => setTargetDate(event.target.value)}
          />
          <small>비우면 FastAPI가 CSV 최신 예측일을 사용합니다.</small>
        </label>

        <label className="sales-upload-checkbox">
          <input
            type="checkbox"
            checked={onlyPositiveRecommendations}
            onChange={(event) => setOnlyPositiveRecommendations(event.target.checked)}
          />
          <span>추천 수량이 1개 이상인 상품만 저장</span>
        </label>

        <div className="sales-upload-actions">
          <button className="sales-upload-button" type="submit" disabled={loading}>
            {loading ? "실행 중..." : "AI 예측 실행"}
          </button>
        </div>
      </form>

      {error && <p className="panel-error">{error}</p>}

      {result && (
        <div className="sales-upload-result">
          <h3>실행 결과</h3>
          <div className="sales-upload-metrics">
            <div>
              <strong>상태</strong>
              <span>{result.status}</span>
            </div>
            <div>
              <strong>대상일</strong>
              <span>{result.targetDate || "-"}</span>
            </div>
            <div>
              <strong>응답 행</strong>
              <span>{result.rowCount}</span>
            </div>
            <div>
              <strong>저장</strong>
              <span>{result.savedCount}</span>
            </div>
          </div>
          <p className="sales-upload-message">{result.runId}</p>
          {result.errorMessage && <p className="panel-error">{result.errorMessage}</p>}
        </div>
      )}
    </div>
  );
}

export default AiRunPanel;
