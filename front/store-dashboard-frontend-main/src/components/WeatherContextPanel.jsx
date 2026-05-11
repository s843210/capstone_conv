import { useMemo, useState } from "react";
import { syncWeatherContext } from "../api/api";

function formatToday() {
  const now = new Date();
  const offsetMs = now.getTimezoneOffset() * 60 * 1000;
  return new Date(now.getTime() - offsetMs).toISOString().slice(0, 10);
}

function WeatherContextPanel() {
  const today = useMemo(() => formatToday(), []);
  const [targetDate, setTargetDate] = useState(today);
  const [dryRun, setDryRun] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setResult(null);
    setLoading(true);

    try {
      const response = await syncWeatherContext({
        targetDate,
        dryRun,
      });
      setResult(response);
    } catch (err) {
      setError(err.message || "날씨/Context 갱신 중 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">
          <span className="panel-icon">WX</span>
          <h2>날씨/Context 갱신</h2>
        </div>
      </div>

      <p className="panel-desc">
        선택한 날짜의 날씨를 조회해 <code>daily_context</code>에 반영합니다.
        공휴일, 학사 이벤트, 유동인구 값도 함께 계산됩니다.
      </p>

      <form className="sales-upload-form" onSubmit={handleSubmit}>
        <label className="sales-upload-field">
          <span>대상 날짜</span>
          <input
            type="date"
            value={targetDate}
            onChange={(event) => setTargetDate(event.target.value)}
          />
          <small>AI 예측 실행 날짜와 같은 날짜로 맞추면 됩니다.</small>
        </label>

        <label className="sales-upload-checkbox">
          <input
            type="checkbox"
            checked={dryRun}
            onChange={(event) => setDryRun(event.target.checked)}
          />
          <span>DRY RUN (DB 저장 없이 조회만 확인)</span>
        </label>

        <div className="sales-upload-actions">
          <button className="sales-upload-button" type="submit" disabled={loading}>
            {loading ? "갱신 중..." : dryRun ? "날씨 조회 테스트" : "날씨/Context 갱신"}
          </button>
        </div>
      </form>

      {error && <p className="panel-error">{error}</p>}

      {result && (
        <div className="sales-upload-result">
          <h3>갱신 결과</h3>
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
              <strong>평균기온</strong>
              <span>{result.avgTempC ?? "-"}</span>
            </div>
            <div>
              <strong>강수량</strong>
              <span>{result.precipitationMm ?? "-"}</span>
            </div>
            <div>
              <strong>비 여부</strong>
              <span>{result.isRain ?? "-"}</span>
            </div>
          </div>
          <p className="sales-upload-message">{result.message || result.runId}</p>
        </div>
      )}
    </div>
  );
}

export default WeatherContextPanel;
