import { useEffect, useMemo, useState } from "react";
import { fetchStudentRequests } from "../api/api";

const POLL_INTERVAL_MS = 5000;

function formatRequestedAt(value) {
  if (!value) return "-";
  const requestedAt = new Date(value);
  if (Number.isNaN(requestedAt.getTime())) return value;

  return requestedAt.toLocaleString("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function normalizeStatus(value) {
  if (!value) return { label: "검토중", code: "reviewing" };
  const text = String(value).trim();
  if (text.includes("완료") || text.includes("반영")) return { label: "반영완료", code: "done" };
  if (text.includes("대기")) return { label: "대기", code: "pending" };
  return { label: "검토중", code: "reviewing" };
}

function StudentRequestPanel({
  limit = 15,
  title = "학생 신청 목록",
  subtitle = "최근 15건 자동 갱신",
  className = "",
}) {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState("전체");

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
      requests.map((request) => {
        const status = normalizeStatus(request.status);
        return {
          ...request,
          statusLabel: status.label,
          statusCode: status.code,
          requestedAtLabel: formatRequestedAt(request.requestedAt),
        };
      }),
    [requests],
  );

  const filteredRequests = useMemo(() => {
    if (statusFilter === "전체") return decoratedRequests;
    return decoratedRequests.filter((request) => request.statusLabel === statusFilter);
  }, [decoratedRequests, statusFilter]);

  const summary = useMemo(() => {
    const total = decoratedRequests.length;
    const pending = decoratedRequests.filter((request) => request.statusCode === "pending").length;
    const reviewing = decoratedRequests.filter((request) => request.statusCode === "reviewing").length;
    const done = decoratedRequests.filter((request) => request.statusCode === "done").length;
    return { total, pending, reviewing, done };
  }, [decoratedRequests]);

  return (
    <>
      <article className="summary-card-grid request-summary-grid">
        <div className="summary-soft-card">
          <span>전체 요청 수</span>
          <strong>{summary.total}</strong>
        </div>
        <div className="summary-soft-card">
          <span>대기 중</span>
          <strong>{summary.pending}</strong>
        </div>
        <div className="summary-soft-card">
          <span>검토 중</span>
          <strong>{summary.reviewing}</strong>
        </div>
        <div className="summary-soft-card">
          <span>반영 완료</span>
          <strong>{summary.done}</strong>
        </div>
      </article>

      <article className={`panel requests-list-panel ${className}`.trim()}>
        <div className="request-toolbar">
          <h2>{title}</h2>
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            <option value="전체">전체 상태</option>
            <option value="대기">대기</option>
            <option value="검토중">검토중</option>
            <option value="반영완료">반영완료</option>
          </select>
        </div>

        {subtitle && <p className="panel-desc">{subtitle}</p>}
        {loading && <p className="panel-desc">요청 현황을 불러오는 중입니다...</p>}
        {!loading && error && <p className="panel-error">{error}</p>}

        {!loading && !error && filteredRequests.length === 0 && (
          <div className="empty-state">
            <div className="empty-icon">📭</div>
            <strong>아직 접수된 학생 신청이 없습니다.</strong>
            <p>학생이 상품을 신청하면 이곳에서 최신 상태를 확인할 수 있습니다.</p>
          </div>
        )}

        {!loading && !error && filteredRequests.length > 0 && (
          <div className="request-card-list">
            {filteredRequests.map((request, idx) => (
              <div className="request-card" key={`${request.studentId}-${request.salesDate}-${request.pluCode}-${idx}`}>
                <div>
                  <strong>{request.productName}</strong>
                  <p>요청 수량 {request.quantity}개</p>
                </div>
                <div className="request-card-meta">
                  <span className={`request-status status-${request.statusCode}`}>{request.statusLabel}</span>
                  <span>{request.requestedAtLabel}</span>
                  <button className="mini-action" type="button">상세보기</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </article>
    </>
  );
}

export default StudentRequestPanel;
