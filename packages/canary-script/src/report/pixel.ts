/**
 * Pixel reporter.
 * Last-resort reporter that encodes minimal payload into image URL query params.
 * Works even in environments where fetch and sendBeacon are blocked.
 */

import type { IngestPayload } from '../types';

/**
 * Encode a minimal subset of the payload into URL-safe query parameters.
 * Keeps the URL under ~2000 characters to fit in most servers/proxies.
 */
function encodeMinimalPayload(payload: IngestPayload): string {
  const params = new URLSearchParams();

  params.set('v', String(payload.v));
  params.set('sk', payload.site_key);
  params.set('vid', payload.visit_id);
  params.set('ts', payload.timestamp);
  params.set('url', payload.page_url.slice(0, 200));
  params.set('conf', payload.detection.confidence.toFixed(2));
  params.set('cls', payload.detection.classification);

  if (payload.detection.agent_family) {
    params.set('af', payload.detection.agent_family.slice(0, 50));
  }

  // Encode test results compactly: testId:outcome pairs
  const testSummary = payload.test_results
    .map(t => `${t.test_id.slice(0, 8)}:${abbreviateOutcome(t.outcome)}`)
    .join(',')
    .slice(0, 500);

  if (testSummary) {
    params.set('tr', testSummary);
  }

  return params.toString();
}

/**
 * Abbreviate outcome strings for compact encoding.
 */
function abbreviateOutcome(outcome: string): string {
  switch (outcome) {
    case 'exfiltration_attempted': return 'ex';
    case 'full_compliance': return 'fc';
    case 'partial_compliance': return 'pc';
    case 'acknowledged': return 'ak';
    case 'ignored': return 'ig';
    default: return outcome.slice(0, 2);
  }
}

/**
 * Send an ingest payload by creating an invisible image element.
 * The payload is encoded as query parameters on the image src.
 *
 * @param endpoint - The API endpoint URL
 * @param payload - The ingest payload to send
 * @returns true if the image element was created (delivery not guaranteed)
 */
export function sendPixel(endpoint: string, payload: IngestPayload): boolean {
  try {
    const queryString = encodeMinimalPayload(payload);
    const separator = endpoint.includes('?') ? '&' : '?';
    const url = `${endpoint}/pixel${separator}${queryString}`;

    // Truncate URL to 2000 chars max
    const finalUrl = url.slice(0, 2000);

    const img = new Image(1, 1);
    img.src = finalUrl;
    img.style.position = 'absolute';
    img.style.left = '-9999px';
    img.style.top = '-9999px';
    img.setAttribute('aria-hidden', 'true');

    // Append briefly to trigger the request, then remove
    document.body.appendChild(img);
    setTimeout(() => {
      try { img.remove(); } catch { /* ignore */ }
    }, 5000);

    return true;
  } catch {
    return false;
  }
}
