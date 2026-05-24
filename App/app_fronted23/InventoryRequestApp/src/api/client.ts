// Production API server.
export const BASE_URL = 'https://coop1925.duckdns.org';

let apiAuthToken: string | null = null;

export function setApiAuthToken(token: string | null): void {
  apiAuthToken = token;
}

export function getApiAuthHeaders(): Record<string, string> {
  if (!apiAuthToken) {
    return {};
  }

  return {
    Authorization: `Bearer ${apiAuthToken}`,
  };
}
