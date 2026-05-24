import {BASE_URL, setApiAuthToken} from './client';

const REQUEST_TIMEOUT_MS = 8000;

export type AuthUserRecord = {
  id: number;
  loginId: string;
  email?: string;
  name: string;
  role: 'ADMIN' | 'STUDENT';
  provider: 'LOCAL' | 'GOOGLE' | 'DEV';
};

export type AuthResponse = {
  accessToken: string;
  tokenType: string;
  user: AuthUserRecord;
};

type GoogleLoginInput = {
  idToken: string;
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

export async function loginGoogle(payload: GoogleLoginInput): Promise<AuthResponse> {
  try {
    const response = await fetchWithTimeout(`${BASE_URL}/api/auth/google`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(await readErrorMessage(response, 'Google 로그인 실패'));
    }

    const auth = (await response.json()) as AuthResponse;
    setApiAuthToken(auth.accessToken);
    return auth;
  } catch (error) {
    if (__DEV__) {
      console.log('[loginGoogle] error', error);
    }
    throw new Error(toUserMessage('Google 로그인 실패', error));
  }
}
