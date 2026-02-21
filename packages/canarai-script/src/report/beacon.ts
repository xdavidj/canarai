/**
 * Beacon reporter.
 * Uses navigator.sendBeacon for reliable delivery, especially during page unload.
 * Sends JSON serialized as text/plain to avoid CORS preflight.
 */

import type { IngestPayload } from '../types';

/**
 * Send an ingest payload via navigator.sendBeacon.
 *
 * @param endpoint - The API endpoint URL
 * @param payload - The ingest payload to send
 * @returns true if the browser accepted the beacon for delivery
 */
export function sendBeacon(endpoint: string, payload: IngestPayload): boolean {
  if (typeof navigator.sendBeacon !== 'function') {
    return false;
  }

  try {
    const data = JSON.stringify(payload);
    // Use Blob with text/plain to avoid CORS preflight
    // The server should parse the body as JSON regardless of Content-Type
    const blob = new Blob([data], { type: 'text/plain' });
    return navigator.sendBeacon(endpoint, blob);
  } catch {
    return false;
  }
}
