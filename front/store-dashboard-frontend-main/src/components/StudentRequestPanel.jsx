import { useEffect, useState } from "react";
import { fetchStudentRequests } from "../api/api";

const POLL_INTERVAL_MS = 5000;

function formatRequestedAt(value) {
  if (!value) {
    return "-";
  }

  const requestedAt = new Date(value);
  if (Number.isNaN(requestedAt.getTime())) {
    return value;
  }

  return requestedAt.toLocaleString("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function StudentRequestPanel({
  limit = 15,
  title = "학생 신청 현황",
  subtitle = "최근 15개 자동 갱신",
  onViewAll,
  viewAllLabel = "전체 보기",
  className = "",
}) {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    const loadRequests = async () => {
      try {
        const data = await fetchStudentRequests({ limit });
        if (!cancelled) {
          setRequests(data);
          setError("");
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || "학생 신청 현황을 불러오지 못했습니다.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    loadRequests();
    const intervalId = window.setInterval(loadRequests, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [limit]);

  return (
    <div className={`panel full-width student-request-panel ${className}`}>
      <div className="panel-header">
        <div className="panel-title">
          <span className="panel-icon">📝</span>
          <h2>{title}</h2>
        </div>
        <div className="panel-header-actions">
          <span>{subtitle}</span>
          {onViewAll && (
            <button className="panel-action-button" type="button" onClick={onViewAll}>
              {viewAllLabel}
            </button>
          )}
        </div>
      </div>

      {loading && <p className="student-request-empty">신청 현황을 불러오는 중입니다...</p>}

      {!loading && error && <p className="panel-error">{error}</p>}

      {!loading && !error && requests.length === 0 && (
        <p className="student-request-empty">아직 접수된 학생 신청이 없습니다.</p>
      )}

      {!loading && !error && requests.length > 0 && (
        <div className="student-request-table-wrap">
          <table className="student-request-table">
            <thead>
              <tr>
                <th>학생 ID</th>
                <th>상품명</th>
                <th>희망 수량</th>
                <th>신청 시각</th>
              </tr>
            </thead>
            <tbody>
              {requests.map((request) => (
                <tr
                  key={`${request.studentId}-${request.salesDate}-${request.pluCode}`}
                >
                  <td>{request.studentId}</td>
                  <td>{request.productName}</td>
                  <td>{request.quantity}개</td>
                  <td>{formatRequestedAt(request.requestedAt)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default StudentRequestPanel;
