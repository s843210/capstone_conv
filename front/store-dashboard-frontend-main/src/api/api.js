const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8080";

function canParseJson(response) {
  const contentType = response.headers.get("content-type") || "";
  return contentType.includes("application/json");
}

async function extractErrorMessage(response) {
  const fallback = `API 요청 실패: ${response.status} ${response.statusText}`;

  try {
    if (canParseJson(response)) {
      const payload = await response.json();
      if (payload && typeof payload.message === "string" && payload.message.trim()) {
        return payload.message;
      }
      return fallback;
    }

    const text = await response.text();
    return text.trim() || fallback;
  } catch {
    return fallback;
  }
}

/**
 * 공통 fetch 유틸리티
 * - res.ok 체크 포함
 * - 에러 시 의미 있는 에러 메시지 throw
 */
async function fetchWithErrorHandling(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`;

  const hasBody = options.body !== undefined && !(options.body instanceof FormData);

  const response = await fetch(url, {
    headers: {
      ...(hasBody ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const message = await extractErrorMessage(response);
    throw new Error(message);
  }

  if (response.status === 204) {
    return null;
  }

  if (canParseJson(response)) {
    return response.json();
  }

  return response.text();
}

/** 대시보드 전체 데이터 조회 */
export function fetchDashboard() {
  return fetchWithErrorHandling("/api/dashboard");
}

/** 재고 목록 페이지네이션 조회 */
export function fetchInventory({
  page,
  size = 30,
  q = "",
  category = "",
  sort = "stock_asc",
}) {
  const params = new URLSearchParams({
    page: String(page),
    size: String(size),
    sort,
  });

  const trimmedQ = q.trim();
  if (trimmedQ) {
    params.set("q", trimmedQ);
  }

  const trimmedCategory = category.trim();
  if (trimmedCategory && trimmedCategory !== "all") {
    params.set("category", trimmedCategory);
  }

  return fetchWithErrorHandling(`/api/inventory?${params.toString()}`);
}

/** 재고 카테고리 목록 조회 */
export function fetchInventoryCategories() {
  return fetchWithErrorHandling("/api/inventory/categories");
}

/** 학생 앱 상품 신청 현황 조회 */
export function fetchStudentRequests({ limit = 15 } = {}) {
  const params = new URLSearchParams({
    limit: String(limit),
  });

  return fetchWithErrorHandling(`/api/student/requests?${params.toString()}`);
}

/** 판매 파일 업로드 후 daily_sales 적재 */
export function uploadDailySales({
  salesFiles,
  masterFiles = [],
  salesDate = "",
  dryRun = false,
}) {
  const formData = new FormData();

  salesFiles.forEach((file) => formData.append("salesFiles", file));
  masterFiles.forEach((file) => formData.append("masterFiles", file));

  const trimmedDate = salesDate.trim();
  if (trimmedDate) {
    formData.append("salesDate", trimmedDate);
  }

  formData.append("dryRun", String(dryRun));

  return fetchWithErrorHandling("/api/admin/sales/upload", {
    method: "POST",
    body: formData,
  });
}

/** 현재고 엑셀/CSV 업로드 후 product.current_stock 반영 */
export function uploadInventoryStock({ file, dryRun = false }) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("dryRun", String(dryRun));

  return fetchWithErrorHandling("/api/admin/inventory/upload", {
    method: "POST",
    body: formData,
  });
}

/** Product master CSV upload for PLU/category mapping */
export function uploadProductMaster({ files, dryRun = false }) {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  formData.append("dryRun", String(dryRun));

  return fetchWithErrorHandling("/api/admin/products/master/upload", {
    method: "POST",
    body: formData,
  });
}

/** Run monthly_v2 AI prediction through Spring -> FastAPI */
export function runAiPrediction({
  targetDate = "",
  onlyPositiveRecommendations = true,
} = {}) {
  const params = new URLSearchParams({
    onlyPositiveRecommendations: String(onlyPositiveRecommendations),
  });

  const trimmedTargetDate = targetDate.trim();
  if (trimmedTargetDate) {
    params.set("targetDate", trimmedTargetDate);
  }

  return fetchWithErrorHandling(`/api/admin/ai/predict?${params.toString()}`, {
    method: "POST",
  });
}

/** Sync weather/context for a target date */
export function syncWeatherContext({ targetDate = "", dryRun = false } = {}) {
  const params = new URLSearchParams({
    dryRun: String(dryRun),
  });

  const trimmedTargetDate = targetDate.trim();
  if (trimmedTargetDate) {
    params.set("targetDate", trimmedTargetDate);
  }

  return fetchWithErrorHandling(`/api/admin/context/weather?${params.toString()}`, {
    method: "POST",
  });
}

/** 학사일정/유동인구 CSV 업로드 */
export function uploadAcademicContext({
  academicFile,
  headcountFile,
  dryRun = false,
}) {
  const formData = new FormData();
  formData.append("academicFile", academicFile);
  if (headcountFile) {
    formData.append("headcountFile", headcountFile);
  }
  formData.append("dryRun", String(dryRun));

  return fetchWithErrorHandling("/api/admin/context/academic/upload", {
    method: "POST",
    body: formData,
  });
}

/** 학사 컨텍스트 기간 백필 */
export function backfillAcademicContext({ from, to, maxDays = 365 }) {
  const params = new URLSearchParams({
    from,
    to,
    maxDays: String(maxDays),
  });

  return fetchWithErrorHandling(`/api/admin/context/academic/backfill?${params.toString()}`, {
    method: "POST",
  });
}
