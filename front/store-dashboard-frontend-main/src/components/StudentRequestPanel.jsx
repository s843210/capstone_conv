import { useEffect, useMemo, useState } from "react";
import { fetchStudentRequests } from "../api/api";
import { formatShortDateTime24 } from "../utils/dateFormat";

const POLL_INTERVAL_MS = 5000;

function StudentRequestPanel({
  limit = 15,
  title = "학생 신청 목록",
  subtitle = "최근 15건 자동 갱신",
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
          setError(err.message || "학생 요청 현황을 불러오지 못했습니다.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    loadRequests();
    const intervalId = window.setInterval(loadRequests, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [limit]);

  const decoratedRequests = useMemo(
    () =>
      requests.map((request) => ({
        ...request,
        requestedAtLabel: formatShortDateTime24(request.requestedAt),
      })),
    [requests],
  );

  return (
    <article className={`panel requests-list-panel ${className}`.trim()}>
      <div className="request-toolbar">
        <h2>{title}</h2>
      </div>

      {subtitle && <p className="panel-desc">{subtitle}</p>}
      {loading && <p className="panel-desc">요청 현황을 불러오는 중입니다...</p>}
      {!loading && error && <p className="panel-error">{error}</p>}

      {!loading && !error && decoratedRequests.length === 0 && (
        <div className="empty-state">
          <div className="empty-icon">📭</div>
          <strong>아직 접수된 학생 신청이 없습니다.</strong>
          <p>학생이 상품을 신청하면 이곳에서 최신 신청을 확인할 수 있습니다.</p>
        </div>
      )}

      {!loading && !error && decoratedRequests.length > 0 && (
        <div className="request-card-list">
          {decoratedRequests.map((request, idx) => (
            <div className="request-card" key={`${request.studentId}-${request.salesDate}-${request.pluCode}-${idx}`}>
              <div>
                <strong>{request.productName}</strong>
                <p>요청 수량 {request.quantity}개</p>
              </div>
              <div className="request-card-meta">
                <span>{request.requestedAtLabel}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </article>
  );
}

export default StudentRequestPanel;
