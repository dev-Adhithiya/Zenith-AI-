import DOMPurify from 'dompurify';

/**
 * Sanitize untrusted HTML (e.g. Gmail body_html) before srcDoc or dangerouslySetInnerHTML.
 */
export function sanitizeEmailHtml(html: string): string {
  return DOMPurify.sanitize(html, {
    USE_PROFILES: { html: true },
  });
}
