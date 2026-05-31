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
        dryRun: false,
      });
      setResult(response);
    } catch (err) {
      setError("날씨/Context 갱신에 실패했습니다.");
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

        <div className="sales-upload-actions">
          <button className="sales-upload-button" type="submit" disabled={loading}>
            {loading ? "갱신 중..." : "날씨/Context 갱신"}
          </button>
        </div>
      </form>

      {error && <p className="panel-error">실패: {error}</p>}

      {result && (
        <div className="sales-upload-result">
          <h3>갱신 결과</h3>
          <div className="sales-upload-status success">
            <strong>성공</strong>
            <span>날씨/Context 갱신이 완료되었습니다.</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default WeatherContextPanel;
