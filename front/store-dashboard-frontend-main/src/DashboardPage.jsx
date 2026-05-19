import { useEffect, useMemo, useState } from "react";
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
import { fetchStudentRequests } from "./api/api";
import { useDashboardData } from "./hooks/useDashboardData";

const POLL_INTERVAL_MS = 5000;
const PAGE_META = {
  dashboard: { title: "운영 대시보드", description: "재고, 수요 예측, 발주 추천 정보를 한눈에 확인합니다." },
  product: { title: "상품 관리", description: "상품 정보와 카테고리를 관리할 수 있습니다." },
  products: { title: "상품 관리", description: "상품 정보와 카테고리를 관리할 수 있습니다." },
  inventory: { title: "재고 관리", description: "현재 재고 상태와 부족 상품을 확인할 수 있습니다." },
  order: { title: "발주 관리", description: "AI 추천 발주량과 발주 현황을 확인할 수 있습니다." },
  analysis: { title: "데이터 분석", description: "판매/재고 데이터를 기반으로 운영 현황을 분석합니다." },
  studentRequests: { title: "학생 신청 관리", description: "학생 상품 요청과 처리 상태를 관리할 수 있습니다." },
  suggestions: { title: "건의사항", description: "사용자 건의사항과 의견을 확인할 수 있습니다." },
  settings: { title: "운영 관리", description: "데이터 업로드 및 운영 설정을 관리합니다." },
};

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
  const [activePage, setActivePage] = useState("dashboard");
  const [studentRequests, setStudentRequests] = useState([]);
  const [requestError, setRequestError] = useState("");
  const [productNameQuery, setProductNameQuery] = useState("");
  const [productPluQuery, setProductPluQuery] = useState("");
  const [productCategory, setProductCategory] = useState("전체");
  const [productSalesStatus, setProductSalesStatus] = useState("전체");
  const [orderQuery, setOrderQuery] = useState("");
  const [orderCategory, setOrderCategory] = useState("전체");
  const [orderSort, setOrderSort] = useState("desc");
  const [orderStockFilter, setOrderStockFilter] = useState("전체");
  const [suggestionQuery, setSuggestionQuery] = useState("");
  const [suggestionStatus, setSuggestionStatus] = useState("전체");
  const [suggestionSort, setSuggestionSort] = useState("latest");

  const {
    loading,
    error,
    inventoryList,
    orderList,
    insights,
    totalItems,
    normalItems,
    lowStockItems,
    refreshDashboard,
  } = useDashboardData();

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

    loadRequests();
    const intervalId = window.setInterval(loadRequests, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, []);

  const inventoryRows = useMemo(
    () =>
      [...inventoryList]
        .sort((a, b) => {
          const ratioA = a.target > 0 ? a.stock / a.target : 1;
          const ratioB = b.target > 0 ? b.stock / b.target : 1;
          return ratioA - ratioB;
        })
        .slice(0, 10),
    [inventoryList],
  );

  const categoryRows = useMemo(() => {
    const groups = new Map();

    inventoryRows.forEach((item) => {
      const key = item.name?.includes("음료")
        ? "음료"
        : item.name?.includes("디저트") || item.name?.includes("빵")
          ? "디저트"
          : item.name?.includes("즉석") || item.name?.includes("간편")
            ? "간편식"
            : "기타";

      const prev = groups.get(key) || { stock: 0, target: 0 };
      groups.set(key, {
        stock: prev.stock + Number(item.stock || 0),
        target: prev.target + Number(item.target || 0),
      });
    });

    return Array.from(groups.entries())
      .map(([name, value]) => {
        const ratio = value.target > 0 ? Math.min((value.stock / value.target) * 100, 100) : 100;
        return { name, ratio: Math.max(0, Math.round(ratio)) };
      })
      .slice(0, 4);
  }, [inventoryRows]);

  const suggestionRows = useMemo(
    () => insights.slice(0, 10).map((item, idx) => ({
      title: item.title,
      preview: item.desc,
      time: idx === 0 ? "방금" : `${idx + 1}분 전`,
    })),
    [insights],
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

  const productRows = useMemo(
    () =>
      inventoryList.map((item, idx) => {
        const stock = Number(item.stock || 0);
        const target = Number(item.target || 0);
        const ratio = target > 0 ? stock / target : 1;
        const category =
          item.name?.includes("음료")
            ? "음료"
            : item.name?.includes("디저트") || item.name?.includes("빵")
              ? "디저트"
              : item.name?.includes("즉석") || item.name?.includes("간편")
                ? "간편식"
                : "기타";
        const salesStatus = ratio < 0.5 ? "판매 대기" : "판매중";
        const salesVolume = Math.max(0, stock);
        const updatedAt = nowLabel;

        return {
          name: item.name,
          plu: `PLU-${String(idx + 1).padStart(4, "0")}`,
          category,
          salesStatus,
          salesVolume,
          updatedAt,
        };
      }),
    [inventoryList, nowLabel],
  );

  const productCategories = useMemo(
    () => ["전체", ...Array.from(new Set(productRows.map((row) => row.category)))],
    [productRows],
  );

  const filteredProductRows = useMemo(
    () =>
      productRows.filter((row) => {
        const byName = !productNameQuery || row.name.toLowerCase().includes(productNameQuery.toLowerCase());
        const byPlu = !productPluQuery || row.plu.toLowerCase().includes(productPluQuery.toLowerCase());
        const byCategory = productCategory === "전체" || row.category === productCategory;
        const bySalesStatus = productSalesStatus === "전체" || row.salesStatus === productSalesStatus;
        return byName && byPlu && byCategory && bySalesStatus;
      }),
    [productRows, productNameQuery, productPluQuery, productCategory, productSalesStatus],
  );

  const productSummary = useMemo(() => {
    const total = productRows.length;
    const onSale = productRows.filter((row) => row.salesStatus === "판매중").length;
    const managed = productRows.filter((row) => row.category !== "기타").length;
    return {
      total,
      onSale,
      managed,
      newItems: Math.min(total, 7),
    };
  }, [productRows]);

  const orderRows = useMemo(
    () =>
      orderList.map((item) => {
        const category =
          item.name?.includes("음료")
            ? "음료"
            : item.name?.includes("디저트") || item.name?.includes("빵")
              ? "디저트"
              : item.name?.includes("즉석") || item.name?.includes("간편")
                ? "간편식"
                : "기타";
        const stock = Number(item.current || 0);
        const recommended = Number(item.recommended || 0);
        const forecast = stock + recommended;
        return {
          name: item.name,
          category,
          stock,
          forecast,
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
      if (orderStockFilter === "부족") return row.stock < row.forecast * 0.5;
      if (orderStockFilter === "여유") return row.stock >= row.forecast * 0.5;
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
    const priority = filteredOrderRows.filter((row) => row.stock < row.forecast * 0.5).length;
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

  const suggestionRowsDetailed = useMemo(
    () =>
      suggestionRows.map((row, idx) => {
        const statusCode = idx % 3 === 0 ? "unread" : idx % 3 === 1 ? "reviewing" : "done";
        const statusLabel = statusCode === "unread" ? "미확인" : statusCode === "reviewing" ? "검토중" : "반영완료";
        return { ...row, statusCode, statusLabel };
      }),
    [suggestionRows],
  );

  const filteredSuggestionRows = useMemo(() => {
    let list = suggestionRowsDetailed.filter(
      (item) =>
        !suggestionQuery ||
        item.title.toLowerCase().includes(suggestionQuery.toLowerCase()) ||
        item.preview.toLowerCase().includes(suggestionQuery.toLowerCase()),
    );

    if (suggestionStatus !== "전체") {
      list = list.filter((item) => item.statusLabel === suggestionStatus);
    }

    if (suggestionSort === "oldest") {
      list = [...list].reverse();
    }
    return list;
  }, [suggestionRowsDetailed, suggestionQuery, suggestionStatus, suggestionSort]);

  const suggestionSummary = useMemo(() => {
    const total = suggestionRowsDetailed.length;
    const unread = suggestionRowsDetailed.filter((item) => item.statusCode === "unread").length;
    const reviewing = suggestionRowsDetailed.filter((item) => item.statusCode === "reviewing").length;
    const done = suggestionRowsDetailed.filter((item) => item.statusCode === "done").length;
    return { total, unread, reviewing, done };
  }, [suggestionRowsDetailed]);

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
      <Sidebar activePage={activePage} onPageChange={setActivePage} onLogout={onLogout} />

      <main className="dashboard-main">
        <header className="top-header dashboard-header" key={`header-${activePage}`}>
          <div>
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
                </div>

                <div className="stat-grid">
                  <div className="stat-card">
                    <span className="stat-label">전체 품목 수</span>
                    <span className="stat-value">{totalItems}</span>
                    <em>개</em>
                  </div>
                  <div className="stat-card">
                    <span className="stat-label">정상 재고</span>
                    <span className="stat-value">{normalItems}</span>
                    <em>개</em>
                  </div>
                  <div className="stat-card">
                    <span className="stat-label">부족 품목</span>
                    <span className="stat-value">{lowStockItems}</span>
                    <em>개</em>
                  </div>
                  <div className="stat-card">
                    <span className="stat-label">정상 비율</span>
                    <span className="stat-value">
                      {totalItems > 0 ? Math.round((normalItems / totalItems) * 100) : 0}
                    </span>
                    <em>%</em>
                  </div>
                </div>

                <div className="inventory-bottom">
                  <div className="low-stock-box">
                    <span>재고 부족 경고</span>
                    <strong>{lowStockItems}</strong>
                    <em>건</em>
                  </div>

                  <div className="category-ratio">
                    <p className="category-ratio-title">카테고리별 재고 충족률</p>
                    {categoryRows.map((row, idx) => {
                      const fillClass = ["blue", "purple", "green", "orange"][idx % 4];
                      return (
                        <div className="ratio-row" key={row.name}>
                          <div className="ratio-top">
                            <span>{row.name}</span>
                            <strong>{row.ratio}%</strong>
                          </div>
                          <div className="ratio-bar">
                            <div className={`ratio-fill ${fillClass}`} style={{ width: `${row.ratio}%` }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                <div className="table-wrap">
                  <div className="thead row">
                    <span>순위</span>
                    <span>상품명</span>
                    <span>재고/기준</span>
                  </div>
                  {inventoryRows.map((item, idx) => (
                    <div className="row" key={`${item.name}-${idx}`}>
                      <span className="rank">{idx + 1}</span>
                      <span className="prod">{item.name}</span>
                      <span className="qty-badge">{item.stock}/{item.target}</span>
                    </div>
                  ))}
                </div>
              </article>

              <article className="panel order-panel">
                <div className="panel-header with-icon">
                  <h2>
                    <span className="head-icon purple" aria-hidden="true">📊</span>
                    우선 발주 추천 상품 TOP10
                  </h2>
                  <button className="mini-action" type="button">전체보기</button>
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
                  <button className="mini-action" type="button" onClick={() => setActivePage("studentRequests")}>전체보기</button>
                </div>

                {requestError && <p className="panel-error">{requestError}</p>}

                <div className="table-wrap small">
                  <div className="thead row request-head">
                    <span>요청 상품명</span>
                    <span>요청 수량</span>
                    <span>요청 상태</span>
                    <span>요청 일시</span>
                  </div>
                  {studentRequests.slice(0, 15).map((request) => (
                    <div className="row request-row" key={`${request.studentId}-${request.salesDate}-${request.pluCode}`}>
                      <span className="prod">{request.productName}</span>
                      <span>{request.quantity}개</span>
                      <span className="request-status">검토중</span>
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
                  <button className="mini-action primary" type="button">등록하기</button>
                </div>

                <div className="table-wrap small">
                  <div className="thead row suggestion-head">
                    <span>제목</span>
                    <span>내용</span>
                    <span>작성 시간</span>
                  </div>
                  {suggestionRows.map((item, idx) => (
                    <div className="row suggestion-row" key={`${item.title}-${idx}`}>
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
              <div className="status-cell">
                <span>데이터 업데이트 주기</span>
                <strong>약 1분</strong>
              </div>
            </section>
          </>
        )}

        {activePage === "inventory" && <InventoryPanel isActive={activePage === "inventory"} />}

        {activePage === "product" && (
          <section className="requests-page">
            <article className="summary-card-grid request-summary-grid">
              <div className="summary-soft-card">
                <span>전체 상품 수</span>
                <strong>{productSummary.total}</strong>
              </div>
              <div className="summary-soft-card">
                <span>판매 중 상품</span>
                <strong>{productSummary.onSale}</strong>
              </div>
              <div className="summary-soft-card">
                <span>관리 대상 상품</span>
                <strong>{productSummary.managed}</strong>
              </div>
              <div className="summary-soft-card">
                <span>최근 등록 상품</span>
                <strong>{productSummary.newItems}</strong>
              </div>
            </article>

            <article className="panel inventory-filter-panel">
              <div className="inventory-tools product-tools">
                <div className="search-wrap">
                  <label htmlFor="product-name-search">상품명 검색</label>
                  <input
                    id="product-name-search"
                    value={productNameQuery}
                    onChange={(event) => setProductNameQuery(event.target.value)}
                    placeholder="상품명 검색"
                  />
                </div>
                <div className="search-wrap">
                  <label htmlFor="product-plu-search">PLU 코드 검색</label>
                  <input
                    id="product-plu-search"
                    value={productPluQuery}
                    onChange={(event) => setProductPluQuery(event.target.value)}
                    placeholder="PLU 코드 검색"
                  />
                </div>
                <div className="select-wrap">
                  <label htmlFor="product-category">카테고리</label>
                  <select
                    id="product-category"
                    value={productCategory}
                    onChange={(event) => setProductCategory(event.target.value)}
                  >
                    {productCategories.map((category) => (
                      <option key={category} value={category}>
                        {category}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="select-wrap">
                  <label htmlFor="product-sales-status">판매 상태</label>
                  <select
                    id="product-sales-status"
                    value={productSalesStatus}
                    onChange={(event) => setProductSalesStatus(event.target.value)}
                  >
                    <option value="전체">전체</option>
                    <option value="판매중">판매중</option>
                    <option value="판매 대기">판매 대기</option>
                  </select>
                </div>
              </div>
            </article>

            <article className="panel inventory-table-panel">
              <div className="inventory-table-head product-table-head">
                <span>상품명</span>
                <span>PLU 코드</span>
                <span>카테고리</span>
                <span>판매 상태</span>
                <span>최근 판매량</span>
                <span>최근 수정일</span>
              </div>

              {filteredProductRows.map((row) => (
                <div className="inventory-table-row product-table-row" key={row.plu}>
                  <span className="item-name">{row.name}</span>
                  <span className="item-plu">{row.plu}</span>
                  <span>{row.category}</span>
                  <span
                    className={`request-status ${
                      row.salesStatus === "판매중" ? "status-done" : "status-pending"
                    }`}
                  >
                    {row.salesStatus}
                  </span>
                  <span>{row.salesVolume}개</span>
                  <span>{row.updatedAt}</span>
                </div>
              ))}
            </article>
          </section>
        )}

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
                  <span>{row.forecast}개</span>
                  <span>
                    <em className="qty-badge">{row.recommended}개</em>
                  </span>
                  <span>
                    {row.stock < row.forecast * 0.5 ? (
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
            <article className="summary-card-grid request-summary-grid">
              <div className="summary-soft-card">
                <span>전체 건의사항 수</span>
                <strong>{suggestionSummary.total}</strong>
              </div>
              <div className="summary-soft-card">
                <span>미확인</span>
                <strong>{suggestionSummary.unread}</strong>
              </div>
              <div className="summary-soft-card">
                <span>검토 중</span>
                <strong>{suggestionSummary.reviewing}</strong>
              </div>
              <div className="summary-soft-card">
                <span>반영 완료</span>
                <strong>{suggestionSummary.done}</strong>
              </div>
            </article>

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
                  <label htmlFor="suggestion-status">상태</label>
                  <select
                    id="suggestion-status"
                    value={suggestionStatus}
                    onChange={(event) => setSuggestionStatus(event.target.value)}
                  >
                    <option value="전체">전체 상태</option>
                    <option value="미확인">미확인</option>
                    <option value="검토중">검토중</option>
                    <option value="반영완료">반영완료</option>
                  </select>
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
                <button className="mini-action primary" type="button">건의사항 등록</button>
              </div>

              {filteredSuggestionRows.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon">💡</div>
                  <strong>아직 등록된 건의사항이 없습니다.</strong>
                  <p>학생 의견이 등록되면 이곳에서 확인할 수 있습니다.</p>
                </div>
              ) : (
                <div className="request-card-list">
                  {filteredSuggestionRows.map((item, idx) => (
                    <div className="request-card" key={`${item.title}-${idx}`}>
                      <div>
                        <strong>{item.title}</strong>
                        <p>{item.preview}</p>
                      </div>
                      <div className="request-card-meta">
                        <span className={`request-status status-${item.statusCode}`}>{item.statusLabel}</span>
                        <span>{item.time}</span>
                        <button className="mini-action" type="button">상세보기</button>
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
            <SalesUploadPanel />
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
