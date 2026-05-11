import { useMemo, useState } from "react";
import { uploadDailySales } from "../api/api";

function SalesUploadPanel() {
  const [salesFiles, setSalesFiles] = useState([]);
  const [masterFiles, setMasterFiles] = useState([]);
  const [salesDate, setSalesDate] = useState("");
  const [dryRun, setDryRun] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const canSubmit = useMemo(() => salesFiles.length > 0 && !loading, [salesFiles.length, loading]);

  const handleSubmit = async (event) => {
    event.preventDefault();

    setError("");
    setResult(null);
    setLoading(true);

    try {
      const payload = await uploadDailySales({
        salesFiles,
        masterFiles,
        salesDate,
        dryRun,
      });
      setResult(payload);
    } catch (err) {
      setError(err.message || "판매 데이터 업로드 중 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">
          <span className="panel-icon">SALES</span>
          <h2>판매 데이터 업로드</h2>
        </div>
      </div>

      <p className="panel-desc">
        일별 판매 파일을 업로드하면 <code>product_master</code> DB 기준으로 PLU를 매칭해서
        <code>daily_sales</code>에 <code>sales_date</code>, <code>plu_code</code>, <code>sales_qty</code>를
        upsert합니다.
      </p>

      <form className="sales-upload-form" onSubmit={handleSubmit}>
        <label className="sales-upload-field">
          <span>판매 파일 (xlsx/csv, 여러 개 선택)</span>
          <input
            type="file"
            accept=".xlsx,.xls,.csv"
            multiple
            onChange={(event) => setSalesFiles(Array.from(event.target.files || []))}
          />
          <small>{salesFiles.length > 0 ? `${salesFiles.length}개 선택됨` : "파일을 선택하세요"}</small>
        </label>

        <label className="sales-upload-field">
          <span>상품 마스터 파일 (선택, DB 마스터 보강용)</span>
          <input
            type="file"
            accept=".csv"
            multiple
            onChange={(event) => setMasterFiles(Array.from(event.target.files || []))}
          />
          <small>{masterFiles.length > 0 ? `${masterFiles.length}개 선택됨` : "DB product_master 사용"}</small>
        </label>

        <label className="sales-upload-field">
          <span>판매일자 (선택, 비우면 파일명에서 자동 추출)</span>
          <input
            type="date"
            value={salesDate}
            onChange={(event) => setSalesDate(event.target.value)}
          />
        </label>

        <label className="sales-upload-checkbox">
          <input
            type="checkbox"
            checked={dryRun}
            onChange={(event) => setDryRun(event.target.checked)}
          />
          <span>DRY RUN (DB 저장 없이 매칭 결과만 확인)</span>
        </label>

        <div className="sales-upload-actions">
          <button className="sales-upload-button" type="submit" disabled={!canSubmit}>
            {loading ? "처리 중..." : dryRun ? "DRY RUN 실행" : "DB 적재 실행"}
          </button>
        </div>
      </form>

      {error && <p className="panel-error">{error}</p>}

      {result && (
        <div className="sales-upload-result">
          <h3>실행 결과</h3>
          <div className="sales-upload-metrics">
            <div>
              <strong>원본 행</strong>
              <span>{result.rawRowCount}</span>
            </div>
            <div>
              <strong>매칭 행</strong>
              <span>{result.matchedRowCount}</span>
            </div>
            <div>
              <strong>미매칭</strong>
              <span>{result.unmatchedRowCount}</span>
            </div>
            <div>
              <strong>적재 대상</strong>
              <span>{result.uniqueDailySalesCount}</span>
            </div>
            <div>
              <strong>신규</strong>
              <span>{result.insertedCount}</span>
            </div>
            <div>
              <strong>갱신</strong>
              <span>{result.updatedCount}</span>
            </div>
          </div>

          <p className="sales-upload-message">{result.message}</p>

          {Array.isArray(result.unmatchedSamples) && result.unmatchedSamples.length > 0 && (
            <div className="sales-upload-unmatched">
              <strong>미매칭 샘플</strong>
              <ul>
                {result.unmatchedSamples.map((name) => (
                  <li key={name}>{name}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default SalesUploadPanel;
