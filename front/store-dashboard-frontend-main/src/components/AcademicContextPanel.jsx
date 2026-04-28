import { useState } from "react";
import { backfillAcademicContext, uploadAcademicContext } from "../api/api";

function AcademicContextPanel() {
  const [academicFile, setAcademicFile] = useState(null);
  const [headcountFile, setHeadcountFile] = useState(null);
  const [dryRun, setDryRun] = useState(true);
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");

  const [loadingUpload, setLoadingUpload] = useState(false);
  const [loadingBackfill, setLoadingBackfill] = useState(false);
  const [error, setError] = useState("");
  const [uploadResult, setUploadResult] = useState(null);
  const [backfillResult, setBackfillResult] = useState(null);

  const handleUpload = async (event) => {
    event.preventDefault();

    if (!academicFile) {
      setError("학사일정 CSV 파일을 선택해 주세요.");
      return;
    }

    setError("");
    setUploadResult(null);
    setBackfillResult(null);
    setLoadingUpload(true);

    try {
      const response = await uploadAcademicContext({
        academicFile,
        headcountFile,
        dryRun,
      });
      setUploadResult(response);

      if (response?.minRuleDate && response?.maxRuleDate) {
        setFromDate(response.minRuleDate);
        setToDate(response.maxRuleDate);
      }
    } catch (err) {
      setError(err.message || "학사 컨텍스트 업로드 중 오류가 발생했습니다.");
    } finally {
      setLoadingUpload(false);
    }
  };

  const handleBackfill = async (event) => {
    event.preventDefault();

    if (!fromDate || !toDate) {
      setError("백필 시작일/종료일을 모두 선택해 주세요.");
      return;
    }

    setError("");
    setBackfillResult(null);
    setLoadingBackfill(true);

    try {
      const response = await backfillAcademicContext({
        from: fromDate,
        to: toDate,
      });
      setBackfillResult(response);
    } catch (err) {
      setError(err.message || "학사 컨텍스트 백필 중 오류가 발생했습니다.");
    } finally {
      setLoadingBackfill(false);
    }
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">
          <span className="panel-icon">🎓</span>
          <h2>학사일정/유동인구 업로드</h2>
        </div>
      </div>

      <p className="panel-desc">
        학사일정 CSV를 업로드해 <code>academic_event</code>를 반영하고,
        학기중(1) 평일(월~금)에는 요일별 <code>building_headcount</code>를 채웁니다.
        시험/축제/계절학기/비학기중 및 주말은 기본값 20이 적용됩니다.
      </p>

      <form className="sales-upload-form" onSubmit={handleUpload}>
        <label className="sales-upload-field">
          <span>학사일정 CSV (필수)</span>
          <input
            type="file"
            accept=".csv"
            onChange={(event) => setAcademicFile(event.target.files?.[0] || null)}
          />
          <small>{academicFile ? academicFile.name : "선택된 파일 없음"}</small>
        </label>

        <label className="sales-upload-field">
          <span>요일별 유동인구 CSV (선택)</span>
          <input
            type="file"
            accept=".csv"
            onChange={(event) => setHeadcountFile(event.target.files?.[0] || null)}
          />
          <small>{headcountFile ? headcountFile.name : "미선택 시 기존/기본값 사용"}</small>
        </label>

        <label className="sales-upload-checkbox">
          <input
            type="checkbox"
            checked={dryRun}
            onChange={(event) => setDryRun(event.target.checked)}
          />
          <span>DRY RUN (DB 저장 없이 파싱 결과만 확인)</span>
        </label>

        <div className="sales-upload-actions">
          <button className="sales-upload-button" type="submit" disabled={loadingUpload}>
            {loadingUpload ? "처리 중..." : dryRun ? "DRY RUN 실행" : "규칙 저장 실행"}
          </button>
        </div>
      </form>

      <form className="sales-upload-form academic-backfill-form" onSubmit={handleBackfill}>
        <div className="academic-backfill-grid">
          <label className="sales-upload-field">
            <span>백필 시작일</span>
            <input type="date" value={fromDate} onChange={(event) => setFromDate(event.target.value)} />
          </label>
          <label className="sales-upload-field">
            <span>백필 종료일</span>
            <input type="date" value={toDate} onChange={(event) => setToDate(event.target.value)} />
          </label>
        </div>
        <div className="sales-upload-actions">
          <button className="sales-upload-button" type="submit" disabled={loadingBackfill}>
            {loadingBackfill ? "백필 중..." : "업로드 규칙으로 백필 실행"}
          </button>
        </div>
      </form>

      {error && <p className="panel-error">⚠️ {error}</p>}

      {uploadResult && (
        <div className="sales-upload-result">
          <h3>업로드 결과</h3>
          <div className="sales-upload-metrics">
            <div>
              <strong>파싱 행</strong>
              <span>{uploadResult.parsedRuleRows}</span>
            </div>
            <div>
              <strong>저장 행</strong>
              <span>{uploadResult.savedRuleRows}</span>
            </div>
            <div>
              <strong>무시 행</strong>
              <span>{uploadResult.ignoredRuleRows}</span>
            </div>
            <div>
              <strong>오류 행</strong>
              <span>{uploadResult.invalidRuleRows}</span>
            </div>
            <div>
              <strong>월~금</strong>
              <span>
                {uploadResult.monday}/{uploadResult.tuesday}/{uploadResult.wednesday}/
                {uploadResult.thursday}/{uploadResult.friday}
              </span>
            </div>
            <div>
              <strong>기본값</strong>
              <span>{uploadResult.defaultCount}</span>
            </div>
          </div>
          <p className="sales-upload-message">{uploadResult.message}</p>
        </div>
      )}

      {backfillResult && (
        <div className="sales-upload-result">
          <h3>백필 결과</h3>
          <div className="sales-upload-metrics">
            <div>
              <strong>성공</strong>
              <span>{backfillResult.successCount}</span>
            </div>
            <div>
              <strong>실패</strong>
              <span>{backfillResult.failureCount}</span>
            </div>
          </div>
          <p className="sales-upload-message">{backfillResult.status}</p>
        </div>
      )}
    </div>
  );
}

export default AcademicContextPanel;
