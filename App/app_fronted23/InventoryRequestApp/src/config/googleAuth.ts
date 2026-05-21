export const GOOGLE_WEB_CLIENT_ID =
  process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID ?? '';
export const GOOGLE_ANDROID_CLIENT_ID =
  process.env.EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID ?? '';
export const GOOGLE_SIGN_IN_SCOPES = ['profile', 'email'];

export const hasGoogleClientId = Boolean(GOOGLE_WEB_CLIENT_ID && GOOGLE_ANDROID_CLIENT_ID);
