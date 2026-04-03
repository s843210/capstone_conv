import { useState, useEffect, useRef, useCallback } from "react";
import { fetchInventory } from "../api/api";

/**
 * 무한스크롤 훅
 * - IntersectionObserver + useRef 기반
 * - 로딩/에러 상태 포함
 * - enabled 플래그로 활성/비활성 제어
 */
export function useInfiniteScroll({
  enabled = true,
  query = "",
  category = "all",
  sort = "stock_asc",
}) {
  const [items, setItems] = useState([]);
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const observerTarget = useRef(null);
  const isRequestInFlight = useRef(false);
  const isPageAdvancePending = useRef(false);

  // 페이지 데이터 로드
  useEffect(() => {
    if (!enabled || !hasMore || isRequestInFlight.current) return;

    let cancelled = false;
    isRequestInFlight.current = true;

    fetchInventory({
      page,
      q: query,
      category,
      sort,
    })
      .then((data) => {
        if (cancelled) return;
        if (Array.isArray(data?.items)) {
          setItems((prev) => [...prev, ...data.items]);
        }
        setHasMore(Boolean(data?.hasNext));
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message);
        }
      })
      .finally(() => {
        isRequestInFlight.current = false;
        isPageAdvancePending.current = false;
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
      // React StrictMode 재실행 시 in-flight 플래그가 남아 다음 요청이 막히지 않도록 정리
      isRequestInFlight.current = false;
      isPageAdvancePending.current = false;
    };
  }, [page, enabled, hasMore, query, category, sort]);

  // IntersectionObserver 설정
  useEffect(() => {
    if (!enabled) return;

    const target = observerTarget.current;
    if (!target) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (
          entries[0].isIntersecting &&
          !loading &&
          hasMore &&
          !isRequestInFlight.current &&
          !isPageAdvancePending.current
        ) {
          isPageAdvancePending.current = true;
          setLoading(true);
          setError(null);
          setPage((prev) => prev + 1);
        }
      },
      { threshold: 0.1 },
    );

    observer.observe(target);
    return () => observer.disconnect();
  }, [enabled, loading, hasMore]);

  /** 스크롤 초기화 (탭 전환 시 사용) */
  const reset = useCallback(() => {
    isRequestInFlight.current = false;
    isPageAdvancePending.current = false;
    setItems([]);
    setPage(0);
    setHasMore(true);
    setError(null);
  }, []);

  return {
    items,
    loading,
    error,
    hasMore,
    observerTarget,
    reset,
  };
}
