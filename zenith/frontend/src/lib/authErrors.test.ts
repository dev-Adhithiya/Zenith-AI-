import { describe, it, expect } from 'vitest';
import { resolveAuthErrorMessage, AUTH_ERROR_MESSAGES } from './authErrors';

describe('resolveAuthErrorMessage', () => {
  it('maps known codes', () => {
    expect(resolveAuthErrorMessage('access_denied')).toBe(AUTH_ERROR_MESSAGES.access_denied);
  });

  it('does not echo long legacy server strings', () => {
    const malicious = encodeURIComponent('<script>alert(1)</script>'.repeat(20));
    expect(resolveAuthErrorMessage(malicious)).toBe('Sign-in failed. Please try again.');
  });
});
