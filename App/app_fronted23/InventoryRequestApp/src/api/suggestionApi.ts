import {BASE_URL, getApiAuthHeaders} from './client';
import {Suggestion} from '../types';

const REQUEST_TIMEOUT_MS = 8000;

export type SuggestionRecord = {
  id: number;
  title: string;
  content: string;
  writer: string;
  status: string;
  createdAt: string;
  updatedAt: string;
};

type CreateSuggestionInput = {
  title: string;
  content: string;
};

type UpdateSuggestionInput = {
  id: string;
  title: string;
  content: string;
};

type DeleteSuggestionInput = {
  id: string;
};

type BulkDeleteSuggestionInput = {
  ids: string[];
};

export type BulkDeleteSuggestionResponse = {
  removedCount: number;
  failedCount: number;
};

function toUserMessage(defaultMessage: string, error: unknown): string {
  if (error instanceof TypeError) {
    return '서버에 연결할 수 없습니다.';
  }

  if (error instanceof Error) {
    return error.message;
  }

  return defaultMessage;
}

async function fetchWithTimeout(url: string, init?: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    return await fetch(url, {
      ...init,
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timeoutId);
  }
}

async function readErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const payload = (await response.json()) as {message?: string};
    return payload?.message || fallback;
  } catch {
    return fallback;
  }
}

function formatDateTime(value?: string): string {
  if (!value) {
    return '';
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString('ko-KR');
}

export function toSuggestion(record: SuggestionRecord): Suggestion {
  const createdAt = formatDateTime(record.createdAt);
  const updatedAt = record.updatedAt && record.updatedAt !== record.createdAt
    ? formatDateTime(record.updatedAt)
    : undefined;

  return {
    id: String(record.id),
    title: record.title,
    content: record.content,
    writer: record.writer,
    status: record.status,
    createdAt,
    updatedAt,
  };
}

export async function fetchSuggestions(): Promise<Suggestion[]> {
  try {
    const params = new URLSearchParams({limit: '500'});
    const response = await fetchWithTimeout(`${BASE_URL}/api/student/suggestions?${params.toString()}`, {
      headers: getApiAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error(await readErrorMessage(response, '건의사항 목록 조회 실패'));
    }

    const records = (await response.json()) as SuggestionRecord[];
    return records.map(toSuggestion);
  } catch (error) {
    if (__DEV__) {
      console.log('[fetchSuggestions] error', error);
    }
    throw new Error(toUserMessage('건의사항 목록 조회 실패', error));
  }
}

export async function createSuggestion(payload: CreateSuggestionInput): Promise<Suggestion> {
  try {
    const response = await fetchWithTimeout(`${BASE_URL}/api/student/suggestions`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json', ...getApiAuthHeaders()},
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(await readErrorMessage(response, '건의사항 저장 실패'));
    }

    return toSuggestion((await response.json()) as SuggestionRecord);
  } catch (error) {
    if (__DEV__) {
      console.log('[createSuggestion] error', error);
    }
    throw new Error(toUserMessage('건의사항 저장 실패', error));
  }
}

export async function updateSuggestion(payload: UpdateSuggestionInput): Promise<Suggestion> {
  try {
    const response = await fetchWithTimeout(`${BASE_URL}/api/student/suggestions/${payload.id}`, {
      method: 'PUT',
      headers: {'Content-Type': 'application/json', ...getApiAuthHeaders()},
      body: JSON.stringify({
        title: payload.title,
        content: payload.content,
      }),
    });

    if (!response.ok) {
      throw new Error(await readErrorMessage(response, '건의사항 수정 실패'));
    }

    return toSuggestion((await response.json()) as SuggestionRecord);
  } catch (error) {
    if (__DEV__) {
      console.log('[updateSuggestion] error', error);
    }
    throw new Error(toUserMessage('건의사항 수정 실패', error));
  }
}

export async function deleteSuggestion(payload: DeleteSuggestionInput): Promise<void> {
  try {
    const response = await fetchWithTimeout(`${BASE_URL}/api/student/suggestions/${payload.id}`, {
      method: 'DELETE',
      headers: getApiAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error(await readErrorMessage(response, '건의사항 삭제 실패'));
    }
  } catch (error) {
    if (__DEV__) {
      console.log('[deleteSuggestion] error', error);
    }
    throw new Error(toUserMessage('건의사항 삭제 실패', error));
  }
}

export async function deleteSuggestionsBulk(
  payload: BulkDeleteSuggestionInput,
): Promise<BulkDeleteSuggestionResponse> {
  try {
    const numericIds = payload.ids
      .map(id => Number(id))
      .filter(id => Number.isFinite(id));

    const response = await fetchWithTimeout(`${BASE_URL}/api/student/suggestions/bulk`, {
      method: 'DELETE',
      headers: {'Content-Type': 'application/json', ...getApiAuthHeaders()},
      body: JSON.stringify({
        ids: numericIds,
      }),
    });

    if (!response.ok) {
      throw new Error(await readErrorMessage(response, '건의사항 삭제 실패'));
    }

    return response.json();
  } catch (error) {
    if (__DEV__) {
      console.log('[deleteSuggestionsBulk] error', error);
    }
    throw new Error(toUserMessage('건의사항 삭제 실패', error));
  }
}
