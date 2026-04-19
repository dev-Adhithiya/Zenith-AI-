/** Stable OAuth error codes from the FastAPI callback (?auth_error=). */
export const AUTH_ERROR_MESSAGES: Record<string, string> = {
  missing_params:
    'Sign-in could not continue because required parameters were missing.',
  invalid_params:
    'Sign-in parameters were invalid or too large. Please try again.',
  invalid_state:
    'Your sign-in session was invalid or expired. Please try again.',
  invalid_code:
    'The authorization response was not accepted. Please try signing in again.',
  session_expired:
    'Your sign-in session expired or the server restarted. Please try again.',
  access_denied: 'Sign-in was cancelled or Google did not grant access.',
  signin_failed: 'Google sign-in could not be completed. Please try again.',
  unexpected:
    'An unexpected error occurred during sign-in. Please try again.',
};

export function resolveAuthErrorMessage(raw: string): string {
  let decoded = raw;
  try {
    decoded = decodeURIComponent(raw);
  } catch {
    /* malformed percent-encoding */
  }
  return AUTH_ERROR_MESSAGES[decoded] ?? 'Sign-in failed. Please try again.';
}
