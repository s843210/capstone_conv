import { useEffect, useMemo, useState } from "react";
import { fetchInventoryCategories } from "../api/api";
import { useInfiniteScroll } from "../hooks/useInfiniteScroll";

const SORT_OPTIONS = [
  { value: "stock_desc", label: "재고 많은 순" },
  { value: "stock_asc", label: "재고 적은 순" },
];

function InventoryList({ isActive, query, category, sort }) {
  const { items, loading, error, hasMore, observerTarget } =
    useInfiniteScroll({
      enabled: isActive,
      query,
      category,
      sort,
    });

  return (
    <>
      {error && (
        <p className="panel-error">데이터를 불러오지 못했습니다: {error}</p>
      )}

      {loading && items.length === 0 && (
        <p className="panel-desc">재고 데이터를 불러오는 중...</p>
      )}

      {!loading && !error && items.length === 0 && (
        <p className="panel-desc">조건에 맞는 재고 데이터가 없습니다.</p>
      )}

      <ul className="item-list">
        {items.map((item) => (
          <li key={item.pluCode}>
            <div>
              <strong>{item.name}</strong>
              <p>
                현재 재고 {item.currentStock}개 / 적정 재고{" "}
                {item.recommendedStock}개
              </p>
              <p className="inventory-meta">PLU: {item.pluCode}</p>
            </div>
            <span
              className={`badge ${item.currentStock < item.recommendedStock ? "danger" : "normal"}`}
            >
              {item.currentStock < item.recommendedStock ? "부족" : "정상"}
            </span>
          </li>
        ))}

        {hasMore && (
          <li ref={observerTarget} className="observer-target">
            {loading ? "로딩 중..." : "스크롤하여 더 보기"}
          </li>
        )}
      </ul>
    </>
  );
}

function InventoryPanel({ isActive }) {
  const [queryInput, setQueryInput] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [sortOrder, setSortOrder] = useState("stock_desc");
  const [categories, setCategories] = useState([]);
  const [categoryError, setCategoryError] = useState(null);

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
        if (Array.isArray(data)) {
          setCategories(data);
        } else {
          setCategories([]);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setCategoryError(err.message);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [isActive]);

  const categoryOptions = useMemo(
    () => ["all", ...categories],
    [categories],
  );

  const inventoryListKey = useMemo(
    () => `${debouncedQuery}::${selectedCategory}::${sortOrder}`,
    [debouncedQuery, selectedCategory, sortOrder],
  );

  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">
          <span className="panel-icon">📦</span>
          <h2>재고 관리</h2>
        </div>
      </div>

      <div className="inventory-toolbar" role="search" aria-label="재고 검색 및 필터">
        <input
          type="search"
          className="inventory-search-input"
          placeholder="상품명 또는 PLU 코드 검색"
          value={queryInput}
          onChange={(event) => setQueryInput(event.target.value)}
        />

        <select
          className="inventory-filter-select"
          value={selectedCategory}
          onChange={(event) => setSelectedCategory(event.target.value)}
        >
          {categoryOptions.map((category) => (
            <option key={category} value={category}>
              {category === "all" ? "전체 카테고리" : category}
            </option>
          ))}
        </select>

        <select
          className="inventory-filter-select"
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

      {categoryError && (
        <p className="panel-desc">카테고리 목록을 가져오지 못했습니다: {categoryError}</p>
      )}

      <InventoryList
        key={inventoryListKey}
        isActive={isActive}
        query={debouncedQuery}
        category={selectedCategory}
        sort={sortOrder}
      />
    </div>
  );
}

export default InventoryPanel;
