import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import "./DashboardPage.css";
import "./dashboardDist.css";
import Sidebar from "./components/Sidebar";
import InventoryPanel from "./components/InventoryPanel";
import AcademicContextPanel from "./components/AcademicContextPanel";
import AiRunPanel from "./components/AiRunPanel";
import InventoryUploadPanel from "./components/InventoryUploadPanel";
import ProductMasterUploadPanel from "./components/ProductMasterUploadPanel";
import SalesUploadPanel from "./components/SalesUploadPanel";
import StudentRequestPage from "./components/StudentRequestPage";
import WeatherContextPanel from "./components/WeatherContextPanel";
import { fetchStudentRequests, fetchStudentSuggestions } from "./api/api";
import { useDashboardData } from "./hooks/useDashboardData";

const POLL_INTERVAL_MS = 5000;
const PAGE_META = {
  dashboard: { title: "운영 대시보드", description: "재고, 수요 예측, 발주 추천 정보를 한눈에 확인합니다." },
  inventory: { title: "재고 관리", description: "현재 재고 상태와 부족 상품을 확인할 수 있습니다." },
  order: { title: "발주 추천", description: "AI 추천 발주량과 발주 현황을 확인할 수 있습니다." },
  analysis: { title: "데이터 분석", description: "판매/재고 데이터를 기반으로 운영 현황을 분석합니다." },
  studentRequests: { title: "학생 신청 관리", description: "학생 상품 신청 목록을 확인할 수 있습니다." },
  suggestions: { title: "건의사항", description: "사용자 건의사항과 의견을 확인할 수 있습니다." },
  settings: { title: "운영 관리", description: "데이터 업로드 및 운영 설정을 관리합니다." },
};
const PAGE_PATHS = {
  dashboard: "/",
  inventory: "/inventory",
  order: "/order",
  studentRequests: "/student-requests",
  suggestions: "/suggestions",
  settings: "/settings",
};
const PATH_TO_PAGE = Object.fromEntries(Object.entries(PAGE_PATHS).map(([page, path]) => [path, page]));

function pathToPage(pathname) {
  const normalizedPath = pathname.replace(/\/+$/, "") || "/";
  return PATH_TO_PAGE[normalizedPath] || "dashboard";
}

function pageToPath(page) {
  return PAGE_PATHS[page] || PAGE_PATHS.dashboard;
}

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

function formatDisplayDate(value) {
  if (!value) return "-";

  if (value instanceof Date) {
    const y = value.getFullYear();
    const m = String(value.getMonth() + 1).padStart(2, "0");
    const d = String(value.getDate()).padStart(2, "0");
    return `${y}.${m}.${d}`;
  }

  const isoMatch = String(value).match(/(\d{4})-(\d{2})-(\d{2})/);
  if (isoMatch) {
    return `${isoMatch[1]}.${isoMatch[2]}.${isoMatch[3]}`;
  }

  const parsed = new Date(value);
  if (!Number.isNaN(parsed.getTime())) {
    const y = parsed.getFullYear();
    const m = String(parsed.getMonth() + 1).padStart(2, "0");
    const d = String(parsed.getDate()).padStart(2, "0");
    return `${y}.${m}.${d}`;
  }

  return String(value);
}

function extractPredictionDate(orderList) {
  for (const item of orderList) {
    const reason = String(item?.reason || "");
    const match = reason.match(/(\d{4}-\d{2}-\d{2})/);
    if (match) return match[1];
  }
  return null;
}

function DashboardPage({ onLogout }) {
  const location = useLocation();
  const navigate = useNavigate();
  const activePage = pathToPage(location.pathname);
  const [isMobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [studentRequests, setStudentRequests] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [requestError, setRequestError] = useState("");
  const [suggestionError, setSuggestionError] = useState("");
  const [orderQuery, setOrderQuery] = useState("");
  const [orderCategory, setOrderCategory] = useState("전체");
  const [orderSort, setOrderSort] = useState("desc");
  const [orderStockFilter, setOrderStockFilter] = useState("전체");
  const [suggestionQuery, setSuggestionQuery] = useState("");
  const [suggestionSort, setSuggestionSort] = useState("latest");

  const {
    loading,
    error,
    inventoryList,
    orderList,
    refreshDashboard,
  } = useDashboardData();

  const handlePageChange = useCallback((page) => {
    navigate(pageToPath(page));
    setMobileSidebarOpen(false);
  }, [navigate]);

  useEffect(() => {
    setMobileSidebarOpen(false);
  }, [activePage]);

  useEffect(() => {
    if (!isMobileSidebarOpen) return undefined;

    const closeOnEscape = (event) => {
      if (event.key === "Escape") {
        setMobileSidebarOpen(false);
      }
    };

    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [isMobileSidebarOpen]);

  useEffect(() => {
    let cancelled = false;

    const loadRequests = async () => {
      try {
        const data = await fetchStudentRequests({ limit: 15 });
        if (!cancelled) {
          setStudentRequests(data);
          setRequestError("");
        }
      } catch (err) {
        if (!cancelled) {
          setRequestError(err.message || "학생 요청 현황을 불러오지 못했습니다.");
        }
      }
    };

    const loadSuggestions = async () => {
      try {
        const data = await fetchStudentSuggestions({ limit: 500 });
        if (!cancelled) {
          setSuggestions(data);
          setSuggestionError("");
        }
      } catch (err) {
        if (!cancelled) {
          setSuggestionError(err.message || "건의사항을 불러오지 못했습니다.");
        }
      }
    };

    loadRequests();
    loadSuggestions();
    const intervalId = window.setInterval(loadRequests, POLL_INTERVAL_MS);
    const suggestionIntervalId = window.setInterval(loadSuggestions, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
      window.clearInterval(suggestionIntervalId);
    };
  }, []);

  const inventoryRows = useMemo(
    () =>
      [...inventoryList]
        .sort((a, b) => Number(b.salesQty || 0) - Number(a.salesQty || 0))
        .slice(0, 10),
    [inventoryList],
  );

  const maxInventorySales = useMemo(
    () => Math.max(...inventoryRows.map((item) => Number(item.salesQty || 0)), 1),
    [inventoryRows],
  );

  const suggestionRows = useMemo(
    () => suggestions.map((item) => ({
      id: item.id,
      title: item.title,
      preview: item.content,
      writer: item.writer,
      time: formatRequestedAt(item.updatedAt || item.createdAt),
    })),
    [suggestions],
  );

  const nowLabel = useMemo(
    () =>
      new Date().toLocaleString("ko-KR", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      }),
    [],
  );
  const dateLabel = useMemo(
    () =>
      new Date().toLocaleDateString("ko-KR", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        weekday: "short",
      }),
    [],
  );
  const currentPageMeta = useMemo(
    () => PAGE_META[activePage] || PAGE_META.dashboard,
    [activePage],
  );

  const orderRows = useMemo(
    () =>
      orderList.map((item) => {
        const category = item.category || "기타/미분류";
        const stock = Number(item.current || 0);
        const predicted = Number(item.predicted || 0);
        const recommended = Number(item.recommended || 0);
        return {
          name: item.name,
          category,
          stock,
          predicted,
          recommended,
        };
      }),
    [orderList],
  );

  const orderCategories = useMemo(
    () => ["전체", ...Array.from(new Set(orderRows.map((row) => row.category)))],
    [orderRows],
  );

  const filteredOrderRows = useMemo(() => {
    const byText = orderRows.filter((row) => !orderQuery || row.name.toLowerCase().includes(orderQuery.toLowerCase()));
    const byCategory = byText.filter((row) => orderCategory === "전체" || row.category === orderCategory);
    const byStock = byCategory.filter((row) => {
      if (orderStockFilter === "부족") return row.stock < row.predicted * 0.75;
      if (orderStockFilter === "여유") return row.stock >= row.predicted * 0.75;
      return true;
    });
    const sorted = [...byStock].sort((a, b) =>
      orderSort === "asc" ? a.recommended - b.recommended : b.recommended - a.recommended,
    );
    return sorted;
  }, [orderRows, orderQuery, orderCategory, orderSort, orderStockFilter]);

  const orderSummary = useMemo(() => {
    const targetCount = filteredOrderRows.length;
    const totalQty = filteredOrderRows.reduce((sum, row) => sum + row.recommended, 0);
    const priority = filteredOrderRows.filter((row) => row.stock < row.predicted * 0.75).length;
    const predictionDate = extractPredictionDate(orderList);
    return {
      targetCount,
      totalQty,
      priority,
      forecastDate: formatDisplayDate(predictionDate || new Date()),
    };
  }, [filteredOrderRows, orderList]);

  const analysisSummary = useMemo(() => {
    const soldProducts = inventoryList.length;
    const totalSalesVolume = orderList.reduce((sum, item) => sum + Number(item.recommended || 0), 0);
    const forecastTargets = orderList.filter((item) => Number(item.recommended || 0) > 0).length;
    return {
      soldProducts,
      totalSalesVolume,
      forecastTargets,
      lastRunAt: nowLabel,
    };
  }, [inventoryList, orderList, nowLabel]);

  const filteredSuggestionRows = useMemo(() => {
    let list = suggestionRows.filter(
      (item) =>
        !suggestionQuery ||
        item.title.toLowerCase().includes(suggestionQuery.toLowerCase()) ||
        item.preview.toLowerCase().includes(suggestionQuery.toLowerCase()),
    );

    if (suggestionSort === "oldest") {
      list = [...list].reverse();
    }
    return list;
  }, [suggestionRows, suggestionQuery, suggestionSort]);

  const analysisCategoryRows = useMemo(() => {
    const groups = new Map();
    inventoryList.forEach((item) => {
      const category =
        item.name?.includes("음료")
          ? "음료"
          : item.name?.includes("디저트") || item.name?.includes("빵")
            ? "디저트"
            : item.name?.includes("즉석") || item.name?.includes("간편")
              ? "간편식"
              : "기타";
      const prev = groups.get(category) || 0;
      groups.set(category, prev + Number(item.stock || 0));
    });
    const total = Array.from(groups.values()).reduce((sum, value) => sum + value, 0) || 1;
    return Array.from(groups.entries())
      .map(([name, value]) => ({
        name,
        ratio: Math.round((value / total) * 100),
      }))
      .sort((a, b) => b.ratio - a.ratio)
      .slice(0, 5);
  }, [inventoryList]);

  const topProducts = useMemo(
    () =>
      [...orderList]
        .sort((a, b) => Number(b.recommended || 0) - Number(a.recommended || 0))
        .slice(0, 5)
        .map((item) => `${item.name} (${item.recommended}개)`),
    [orderList],
  );

  const risingProducts = useMemo(
    () =>
      [...inventoryList]
        .sort((a, b) => Number(b.stock || 0) - Number(a.stock || 0))
        .slice(0, 5)
        .map((item) => `${item.name} (재고 ${item.stock})`),
    [inventoryList],
  );

  const fallingProducts = useMemo(
    () =>
      [...inventoryList]
        .sort((a, b) => Number(a.stock || 0) - Number(b.stock || 0))
        .slice(0, 5)
        .map((item) => `${item.name} (재고 ${item.stock})`),
    [inventoryList],
  );

  return (
    <div className="dashboard-layout dashboard-dist">
      <Sidebar
        activePage={activePage}
        isOpen={isMobileSidebarOpen}
        onClose={() => setMobileSidebarOpen(false)}
        onPageChange={handlePageChange}
        onLogout={onLogout}
      />
      {isMobileSidebarOpen && (
        <button
          className="sidebar-backdrop"
          type="button"
          aria-label="메뉴 닫기"
          onClick={() => setMobileSidebarOpen(false)}
        />
      )}

      <main className="dashboard-main">
        <header className="top-header dashboard-header" key={`header-${activePage}`}>
          <div>
            <button
              className="mobile-menu-btn"
              type="button"
              aria-label="메뉴 열기"
              onClick={() => setMobileSidebarOpen(true)}
            >
              ☰
            </button>
            <h1>{currentPageMeta.title}</h1>
            <p>{currentPageMeta.description}</p>
          </div>
          <div className="header-right">
            <span className="header-chip">{dateLabel}</span>
            <span className="admin-chip">관리자</span>
            <button className="icon-btn" type="button" aria-label="알림">🔔</button>
          </div>
        </header>

        {loading && <div className="loading-state">데이터를 불러오는 중...</div>}
        {error && <div className="error-state">데이터를 불러오지 못했습니다. {error}</div>}

        {!loading && !error && activePage === "dashboard" && (
          <>
            <section className="content-grid dashboard-grid">
              <article className="panel inventory-panel">
                <div className="panel-header with-icon">
                  <h2>
                    <span className="head-icon" aria-hidden="true">📦</span>
                    재고 현황
                  </h2>
                  <button
                    className="mini-action primary"
                    type="button"
                    onClick={() => handlePageChange("inventory")}
                  >
                    전체보기
                  </button>
                </div>

                <div className="sales-leaderboard">
                  <div className="leaderboard-head">
                    <div>
                      <span>최근 파일 판매량</span>
                      <strong>TOP 10</strong>
                    </div>
                    <span className="leaderboard-chip">최신 업로드</span>
                  </div>

                  <div className="leaderboard-list">
                    {inventoryRows.map((item, idx) => {
                      const salesQty = Number(item.salesQty || 0);
                      const percentage = Math.max(8, Math.round((salesQty / maxInventorySales) * 100));
                      return (
                        <div className={`leaderboard-item rank-${idx + 1}`} key={`${item.name}-${idx}`}>
                          <span className="leaderboard-rank">{idx + 1}</span>
                          <div className="leaderboard-info">
                            <strong>{item.name}</strong>
                            <div className="leaderboard-bar" aria-hidden="true">
                              <span style={{ width: `${percentage}%` }} />
                            </div>
                          </div>
                          <span className="leaderboard-value">{salesQty}개</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </article>

              <article className="panel order-panel">
                <div className="panel-header with-icon">
                  <h2>
                    <span className="head-icon purple" aria-hidden="true">📊</span>
                    우선 발주 추천 상품 TOP10
                  </h2>
                  <button className="mini-action" type="button" onClick={() => handlePageChange("order")}>
                    전체보기
                  </button>
                </div>

                <div className="table-wrap">
                  <div className="thead row">
                    <span>순위</span>
                    <span>상품명</span>
                    <span>추천 발주량</span>
                  </div>
                  {orderList.slice(0, 10).map((item, idx) => (
                    <div className="row" key={`${item.name}-${idx}`}>
                      <span className="rank">{idx + 1}</span>
                      <span className="prod">{item.name}</span>
                      <span className="qty-badge">{item.recommended}개</span>
                    </div>
                  ))}
                </div>
              </article>

              <article className="panel">
                <div className="panel-header with-icon">
                  <h2>
                    <span className="head-icon" aria-hidden="true">📨</span>
                    학생 요청 현황
                  </h2>
                  <button className="mini-action" type="button" onClick={() => handlePageChange("studentRequests")}>전체보기</button>
                </div>

                {requestError && <p className="panel-error">{requestError}</p>}

                <div className="table-wrap small">
                  <div className="thead row request-head">
                    <span>요청 상품명</span>
                    <span>요청 수량</span>
                    <span>요청 일시</span>
                  </div>
                  {studentRequests.slice(0, 15).map((request) => (
                    <div className="row request-row" key={`${request.studentId}-${request.salesDate}-${request.pluCode}`}>
                      <span className="prod">{request.productName}</span>
                      <span>{request.quantity}개</span>
                      <span>{formatRequestedAt(request.requestedAt)}</span>
                    </div>
                  ))}
                </div>
              </article>

              <article className="panel">
                <div className="panel-header with-icon">
                  <h2>
                    <span className="head-icon" aria-hidden="true">💭</span>
                    건의사항
                  </h2>
                  <button
                    className="mini-action primary"
                    type="button"
                    onClick={() => handlePageChange("suggestions")}
                  >
                    전체확인
                  </button>
                </div>

                <div className="table-wrap small">
                  <div className="thead row suggestion-head">
                    <span>제목</span>
                    <span>내용</span>
                    <span>작성 시간</span>
                  </div>
                  {suggestionError && <p className="panel-error">{suggestionError}</p>}
                  {suggestionRows.slice(0, 10).map((item, idx) => (
                    <div className="row suggestion-row" key={`${item.id || item.title}-${idx}`}>
                      <span className="prod">{item.title}</span>
                      <span className="preview">{item.preview}</span>
                      <span>{item.time}</span>
                    </div>
                  ))}
                </div>
              </article>
            </section>

            <section className="status-bar">
              <div className="status-cell">
                <span>서비스 상태</span>
                <strong>정상 운영 중</strong>
              </div>
              <div className="status-cell">
                <span>최근 데이터 반영</span>
                <strong>{nowLabel}</strong>
              </div>
              <div className="status-cell">
                <span>최근 예측 실행</span>
                <strong>{orderList.length > 0 ? "완료" : "대기"}</strong>
              </div>
              <div className="status-cell">
                <span>다음 점검 항목</span>
                <strong>재고/요청 동기화</strong>
              </div>
            </section>
          </>
        )}

        {activePage === "inventory" && <InventoryPanel isActive={activePage === "inventory"} />}

        {activePage === "order" && (
          <section className="requests-page">
            <article className="summary-card-grid request-summary-grid">
              <div className="summary-soft-card">
                <span>오늘 발주 대상 상품 수</span>
                <strong>{orderSummary.targetCount}</strong>
              </div>
              <div className="summary-soft-card">
                <span>추천 발주 총량</span>
                <strong>{orderSummary.totalQty}</strong>
              </div>
              <div className="summary-soft-card">
                <span>우선 발주 상품 수</span>
                <strong>{orderSummary.priority}</strong>
              </div>
              <div className="summary-soft-card">
                <span>기준 예측 날짜</span>
                <strong>{orderSummary.forecastDate}</strong>
              </div>
            </article>

            <article className="panel inventory-filter-panel">
              <div className="inventory-tools product-tools">
                <div className="search-wrap">
                  <label htmlFor="order-search">상품 검색</label>
                  <input
                    id="order-search"
                    value={orderQuery}
                    onChange={(event) => setOrderQuery(event.target.value)}
                    placeholder="상품명 검색"
                  />
                </div>
                <div className="select-wrap">
                  <label htmlFor="order-category">카테고리</label>
                  <select
                    id="order-category"
                    value={orderCategory}
                    onChange={(event) => setOrderCategory(event.target.value)}
                  >
                    {orderCategories.map((category) => (
                      <option key={category} value={category}>
                        {category}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="select-wrap">
                  <label htmlFor="order-sort">발주량 정렬</label>
                  <select
                    id="order-sort"
                    value={orderSort}
                    onChange={(event) => setOrderSort(event.target.value)}
                  >
                    <option value="desc">높은 순</option>
                    <option value="asc">낮은 순</option>
                  </select>
                </div>
                <div className="select-wrap">
                  <label htmlFor="order-stock-filter">재고 상태</label>
                  <select
                    id="order-stock-filter"
                    value={orderStockFilter}
                    onChange={(event) => setOrderStockFilter(event.target.value)}
                  >
                    <option value="전체">전체</option>
                    <option value="부족">부족</option>
                    <option value="여유">여유</option>
                  </select>
                </div>
              </div>
            </article>

            <article className="panel inventory-table-panel">
              <div className="inventory-table-head order-table-head">
                <span>순위</span>
                <span>상품명</span>
                <span>현재 재고</span>
                <span>예측 판매량</span>
                <span>추천 발주량</span>
                <span>상태</span>
              </div>

              {filteredOrderRows.map((row, idx) => (
                <div className="inventory-table-row order-table-row" key={`${row.name}-${idx}`}>
                  <span>{idx + 1}</span>
                  <span className="item-name">{row.name}</span>
                  <span>{row.stock}개</span>
                  <span>{row.predicted}개</span>
                  <span>
                    <em className="qty-badge">{row.recommended}개</em>
                  </span>
                  <span>
                    {row.stock < row.predicted * 0.75 ? (
                      <span className="soft-status is-check">우선</span>
                    ) : (
                      <span className="soft-status is-watch">일반</span>
                    )}
                  </span>
                </div>
              ))}
            </article>
          </section>
        )}

        {activePage === "analysis" && (
          <section className="requests-page">
            <article className="summary-card-grid request-summary-grid">
              <div className="summary-soft-card">
                <span>오늘 판매 상품 수</span>
                <strong>{analysisSummary.soldProducts}</strong>
              </div>
              <div className="summary-soft-card">
                <span>총 판매량</span>
                <strong>{analysisSummary.totalSalesVolume}</strong>
              </div>
              <div className="summary-soft-card">
                <span>예측 대상 상품 수</span>
                <strong>{analysisSummary.forecastTargets}</strong>
              </div>
              <div className="summary-soft-card">
                <span>최근 예측 실행 시간</span>
                <strong>{analysisSummary.lastRunAt}</strong>
              </div>
            </article>

            <article className="content-grid analysis-grid">
              <article className="panel">
                <div className="panel-header">
                  <h2>카테고리별 판매 비율</h2>
                </div>
                {analysisCategoryRows.map((row) => (
                  <div className="ratio-row analysis-ratio-row" key={row.name}>
                    <div className="ratio-top">
                      <span>{row.name}</span>
                      <strong>{row.ratio}%</strong>
                    </div>
                    <div className="ratio-bar">
                      <div className="ratio-fill blue" style={{ width: `${row.ratio}%` }} />
                    </div>
                  </div>
                ))}
              </article>

              <article className="panel">
                <div className="panel-header">
                  <h2>인기 상품 TOP5</h2>
                </div>
                <ul className="simple-list">
                  {topProducts.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </article>

              <article className="panel">
                <div className="panel-header">
                  <h2>최근 판매 증가 상품</h2>
                </div>
                <ul className="simple-list">
                  {risingProducts.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </article>

              <article className="panel">
                <div className="panel-header">
                  <h2>최근 판매 감소 상품</h2>
                </div>
                <ul className="simple-list">
                  {fallingProducts.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </article>
            </article>
          </section>
        )}

        {activePage === "suggestions" && (
          <section className="requests-page">
            <article className="panel inventory-filter-panel">
              <div className="inventory-tools suggestion-tools">
                <div className="search-wrap">
                  <label htmlFor="suggestion-search">검색</label>
                  <input
                    id="suggestion-search"
                    type="text"
                    placeholder="제목 또는 내용 검색"
                    value={suggestionQuery}
                    onChange={(event) => setSuggestionQuery(event.target.value)}
                  />
                </div>
                <div className="select-wrap">
                  <label htmlFor="suggestion-sort">정렬</label>
                  <select
                    id="suggestion-sort"
                    value={suggestionSort}
                    onChange={(event) => setSuggestionSort(event.target.value)}
                  >
                    <option value="latest">최신순</option>
                    <option value="oldest">오래된순</option>
                  </select>
                </div>
              </div>
            </article>

            <article className="panel requests-list-panel">
              <div className="request-toolbar">
                <h2>건의사항 목록</h2>
              </div>

              {suggestionError && <p className="panel-error">{suggestionError}</p>}

              {filteredSuggestionRows.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon">💡</div>
                  <strong>아직 등록된 건의사항이 없습니다.</strong>
                  <p>학생 의견이 등록되면 이곳에서 확인할 수 있습니다.</p>
                </div>
              ) : (
                <div className="request-card-list">
                  {filteredSuggestionRows.map((item, idx) => (
                    <div className="request-card" key={`${item.id || item.title}-${idx}`}>
                      <div>
                        <strong>{item.title}</strong>
                        <p>{item.preview}</p>
                        <p>작성자: {item.writer || "-"}</p>
                      </div>
                      <div className="request-card-meta">
                        <span>{item.time}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </article>
          </section>
        )}

        {activePage === "studentRequests" && <StudentRequestPage />}

        {activePage === "settings" && (
          <div className="settings-stack">
            <SalesUploadPanel onUploadComplete={() => refreshDashboard().catch(() => {})} />
            <InventoryUploadPanel />
            <WeatherContextPanel />
            <AiRunPanel onPredictionComplete={() => refreshDashboard().catch(() => {})} />
            <ProductMasterUploadPanel />
            <AcademicContextPanel />
          </div>
        )}
      </main>
    </div>
  );
}

export default DashboardPage;
