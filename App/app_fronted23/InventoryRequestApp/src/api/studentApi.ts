// 학생 상품 조회/요청 저장 API 함수 모음
import {BASE_URL} from './client';
import {Product} from '../types';

const REQUEST_TIMEOUT_MS = 8000;

export type StudentRequestItemInput = {
  pluCode: string;
  quantity: number;
};

export type SubmitStudentRequestInput = {
  studentId: string;
  salesDate?: string;
  items: StudentRequestItemInput[];
};

export type SubmitStudentRequestResponse = {
  studentId: string;
  salesDate: string;
  itemCount: number;
  totalQuantity: number;
  message: string;
};

export type DeleteStudentRequestInput = {
  studentId: string;
  salesDate?: string;
  pluCode: string;
};

export type StudentRequestRecord = {
  studentId: string;
  salesDate: string;
  pluCode: string;
  productName: string;
  quantity: number;
  requestedAt: string;
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

export async function fetchStudentProducts(): Promise<Product[]> {
  try {
    const response = await fetchWithTimeout(`${BASE_URL}/api/student/products`);

    if (!response.ok) {
      throw new Error('상품 목록 조회 실패');
    }

    return response.json();
  } catch (error) {
    if (__DEV__) {
      console.log('[fetchStudentProducts] error', error);
    }
    throw new Error(toUserMessage('상품 목록 조회 실패', error));
  }
}

export async function submitStudentRequest(
  payload: SubmitStudentRequestInput,
): Promise<SubmitStudentRequestResponse> {
  try {
    const response = await fetchWithTimeout(`${BASE_URL}/api/student/requests`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        studentId: payload.studentId,
        salesDate: payload.salesDate,
        items: payload.items,
      }),
    });

    if (!response.ok) {
      let message = '신청 저장 실패';

      try {
        const errorData = (await response.json()) as {message?: string};
        if (errorData?.message) {
          message = errorData.message;
        }
      } catch {
        // 응답이 JSON이 아니면 기본 메시지를 사용
      }

      throw new Error(message);
    }

    return response.json();
  } catch (error) {
    if (__DEV__) {
      console.log('[submitStudentRequest] error', error);
    }
    throw new Error(toUserMessage('신청 저장 실패', error));
  }
}

export async function fetchStudentRequests(studentId: string): Promise<StudentRequestRecord[]> {
  try {
    const params = new URLSearchParams({
      studentId,
      limit: '100',
    });

    const response = await fetchWithTimeout(`${BASE_URL}/api/student/requests?${params.toString()}`);

    if (!response.ok) {
      throw new Error('내 요청 목록 조회 실패');
    }

    return response.json();
  } catch (error) {
    if (__DEV__) {
      console.log('[fetchStudentRequests] error', error);
    }
    throw new Error(toUserMessage('내 요청 목록 조회 실패', error));
  }
}

export async function deleteStudentRequest(
  payload: DeleteStudentRequestInput,
): Promise<void> {
  try {
    const params = new URLSearchParams({
      studentId: payload.studentId,
      pluCode: payload.pluCode,
    });

    if (payload.salesDate) {
      params.set('salesDate', payload.salesDate);
    }

    const response = await fetchWithTimeout(`${BASE_URL}/api/student/requests?${params.toString()}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error('신청 삭제 실패');
    }
  } catch (error) {
    if (__DEV__) {
      console.log('[deleteStudentRequest] error', error);
    }
    throw new Error(toUserMessage('신청 삭제 실패', error));
  }
}
