// 학생 상품 조회/요청 저장 API 함수 모음
import {BASE_URL} from './client';
import {Product} from '../types';

export type StudentRequestItemInput = {
  pluCode: string;
  quantity: number;
};

export type SubmitStudentRequestInput = {
  studentId: string;
  items: StudentRequestItemInput[];
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

export async function fetchStudentProducts(): Promise<Product[]> {
  try {
    const response = await fetch(`${BASE_URL}/api/student/products`);

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
): Promise<unknown> {
  try {
    const response = await fetch(`${BASE_URL}/api/student/requests`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        studentId: payload.studentId,
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
