import { useEffect, useMemo, useState } from "react";
import { fetchInventoryCategories } from "../api/api";
import { useInfiniteScroll } from "../hooks/useInfiniteScroll";

const SORT_OPTIONS = [
  { value: "name", label: "상품명 순" },
  { value: "stock_asc", label: "현재 재고 적은 순" },
  { value: "stock_desc", label: "현재 재고 많은 순" },
  { value: "diff_asc", label: "차이 적은 순" },
  { value: "diff_desc", label: "차이 많은 순" },
];

function InventoryPanel({ isActive }) {
  const [queryInput, setQueryInput] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [sortOrder, setSortOrder] = useState("stock_desc");
  const [categories, setCategories] = useState([]);
  const [categoryError, setCategoryError] = useState(null);

  const { items, loading, error, hasMore, observerTarget } = useInfiniteScroll({
    enabled: isActive,
    query: debouncedQuery,
    category: selectedCategory,
    sort: sortOrder,
  });

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      setDebouncedQuery(queryInput);
    }, 300);
    return () => clearTimeout(timeoutId);
  }, [queryInput]);

  useEffect(() => {
    if (!isActive) return;

    let cancelled = false;
    fetchInventoryCategories()
      .then((data) => {
        if (cancelled) return;
        setCategoryError(null);
        setCategories(Array.isArray(data) ? data : []);
      })
      .catch((err) => {
        if (!cancelled) {
          setCategoryError(err.message || "카테고리 목록을 불러오지 못했습니다.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [isActive]);

  const categoryOptions = useMemo(() => ["all", ...categories], [categories]);

  const sortedItems = useMemo(() => {
    const list = [...items];
    if (sortOrder === "name") {
      list.sort((a, b) => String(a.name).localeCompare(String(b.name), "ko"));
    } else if (sortOrder === "diff_asc") {
      list.sort(
        (a, b) =>
          Number(a.currentStock || 0) - Number(a.recommendedStock || 0) -
          (Number(b.currentStock || 0) - Number(b.recommendedStock || 0)),
      );
    } else if (sortOrder === "diff_desc") {
      list.sort(
        (a, b) =>
          Number(b.currentStock || 0) - Number(b.recommendedStock || 0) -
          (Number(a.currentStock || 0) - Number(a.recommendedStock || 0)),
      );
    }
    return list;
  }, [items, sortOrder]);

  const summary = useMemo(() => {
    const total = sortedItems.length;
    const checkTargets = sortedItems.filter(
      (item) => Number(item.currentStock || 0) < Number(item.recommendedStock || 0),
    ).length;
    return {
      total,
      checkTargets,
      orderNeeded: checkTargets,
    };
  }, [sortedItems]);

  return (
    <section className="inventory-page">
      <article className="panel inventory-filter-panel">
        <div className="inventory-tools">
          <div className="search-wrap">
            <label htmlFor="inventory-search">검색</label>
            <input
              id="inventory-search"
              type="text"
              placeholder="상품명 또는 PLU 코드 검색"
              value={queryInput}
              onChange={(event) => setQueryInput(event.target.value)}
            />
          </div>

          <div className="select-wrap">
            <label htmlFor="inventory-category">카테고리</label>
            <select
              id="inventory-category"
              value={selectedCategory}
              onChange={(event) => setSelectedCategory(event.target.value)}
            >
              {categoryOptions.map((category) => (
                <option key={category} value={category}>
                  {category === "all" ? "전체 카테고리" : category}
                </option>
              ))}
            </select>
          </div>

          <div className="select-wrap">
            <label htmlFor="inventory-sort">정렬</label>
            <select
              id="inventory-sort"
              value={sortOrder}
              onChange={(event) => setSortOrder(event.target.value)}
            >
              {SORT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </article>

      <article className="summary-card-grid">
        <div className="summary-soft-card">
          <span>전체 상품 수</span>
          <strong>{summary.total}</strong>
        </div>
        <div className="summary-soft-card">
          <span>재고 확인 대상</span>
          <strong>{summary.checkTargets}</strong>
        </div>
        <div className="summary-soft-card">
          <span>발주 필요 상품</span>
          <strong>{summary.orderNeeded}</strong>
        </div>
      </article>

      <article className="panel inventory-table-panel">
        <div className="inventory-table-head">
          <span>상품명</span>
          <span>PLU 코드</span>
          <span>현재 재고</span>
          <span>적정 재고</span>
          <span>차이</span>
          <span>관리 상태</span>
        </div>

        {categoryError && <p className="panel-desc">카테고리 조회 오류: {categoryError}</p>}
        {error && <p className="panel-error">데이터를 불러오지 못했습니다. {error}</p>}
        {loading && sortedItems.length === 0 && <p className="panel-desc">재고 데이터를 불러오는 중...</p>}
        {!loading && !error && sortedItems.length === 0 && (
          <p className="panel-desc">조건에 맞는 재고 데이터가 없습니다.</p>
        )}

        {sortedItems.map((item) => {
          const current = Number(item.currentStock || 0);
          const target = Number(item.recommendedStock || 0);
          const diff = current - target;
          const status = diff < 0 ? "부족" : "정상";
          return (
            <div className="inventory-table-row" key={item.pluCode}>
              <span className="item-name">{item.name}</span>
              <span className="item-plu">{item.pluCode}</span>
              <span>{current}</span>
              <span>{target}</span>
              <span className={diff < 0 ? "diff-negative" : "diff-positive"}>
                {diff > 0 ? `+${diff}` : diff}
              </span>
              <span>{status}</span>
            </div>
          );
        })}

        {hasMore && (
          <div ref={observerTarget} className="inventory-table-row observer-row">
            <span>더 불러오는 중...</span>
            <span />
            <span />
            <span />
            <span />
            <span />
          </div>
        )}
      </article>
    </section>
  );
}

export default InventoryPanel;
