import { useMemo, useState } from "react";
import { uploadInventoryStock } from "../api/api";

function InventoryUploadPanel() {
  const [file, setFile] = useState(null);
  const [dryRun, setDryRun] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const canSubmit = useMemo(() => {
    return Boolean(file) && !loading;
  }, [file, loading]);

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!file) {
      setError("현재고 엑셀 또는 CSV 파일을 선택해 주세요.");
      return;
    }

    setError("");
    setResult(null);
    setLoading(true);

    try {
      const response = await uploadInventoryStock({ file, dryRun });
      setResult(response);
    } catch (err) {
      setError("현재고 업로드에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">
          <span className="panel-icon">재고</span>
          <h2>현재고 업로드</h2>
        </div>
      </div>

      <p className="panel-desc">
        현재고 파일의 <code>PLU코드</code>, <code>상품명</code>, <code>현재고</code> 컬럼을 읽어
        <code>product.current_stock</code>에 반영합니다. 상품명은 검증용이며 업데이트 기준은 PLU코드입니다.
      </p>

      <form className="sales-upload-form" onSubmit={handleSubmit}>
        <label className="sales-upload-field">
          <span>현재고 파일 (xlsx/csv)</span>
          <input
            type="file"
            accept=".xlsx,.xls,.csv"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
          />
          <small>{file ? file.name : "선택된 파일 없음"}</small>
        </label>

        <label className="sales-upload-checkbox">
          <input
            type="checkbox"
            checked={dryRun}
            onChange={(event) => setDryRun(event.target.checked)}
          />
          <span>DRY RUN (DB 저장 없이 실행 테스트)</span>
        </label>

        <div className="sales-upload-actions">
          <button className="sales-upload-button" type="submit" disabled={!canSubmit}>
            {loading ? "처리 중..." : dryRun ? "DRY RUN 실행" : "재고 반영 실행"}
          </button>
        </div>
      </form>

      {error && <p className="panel-error">실패: {error}</p>}

      {result && (
        <div className="sales-upload-result">
          <h3>실행 결과</h3>
          <div className="sales-upload-status success">
            <strong>성공</strong>
            <span>{dryRun ? "실행 테스트가 완료되었습니다." : "현재고 업로드가 완료되었습니다."}</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default InventoryUploadPanel;
