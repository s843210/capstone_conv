import { useMemo, useState } from "react";
import { uploadDailySales } from "../api/api";

function SalesUploadPanel({ onUploadComplete }) {
  const [salesFiles, setSalesFiles] = useState([]);
  const [masterFiles, setMasterFiles] = useState([]);
  const [salesDate, setSalesDate] = useState("");
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
        dryRun: false,
      });
      setResult(payload);
      onUploadComplete?.(payload);
    } catch (err) {
      setError("판매 데이터 업로드에 실패했습니다.");
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

        <div className="sales-upload-actions">
          <button className="sales-upload-button" type="submit" disabled={!canSubmit}>
            {loading ? "처리 중..." : "DB 적재 실행"}
          </button>
        </div>
      </form>

      {error && <p className="panel-error">실패: {error}</p>}

      {result && (
        <div className="sales-upload-result">
          <h3>실행 결과</h3>
          <div className="sales-upload-status success">
            <strong>성공</strong>
            <span>판매 데이터 업로드가 완료되었습니다.</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default SalesUploadPanel;
