/**
 * Fetch reporter.
 * Fallback reporter using fetch() with keepalive for reliable delivery.
 * Used when navigator.sendBeacon is unavailable.
 */

import type { IngestPayload } from '../types';

/**
 * Send an ingest payload via fetch with keepalive.
 *
 * SECURITY (M-5/M-6): Accepts an optional fetchFn parameter so callers can
 * pass the native fetch reference captured at module load time. This prevents
 * our reporting requests from going through monkey-patched fetch (either our
 * own network observer or third-party patches), which could cause infinite
 * loops or allow interception of canary report data.
 *
 * @param endpoint - The API endpoint URL
 * @param payload - The ingest payload to send
 * @param fetchFn - Optional fetch function to use (defaults to window.fetch)
 * @returns Promise resolving to true if the request succeeded
 */
export async function sendFetch(
  endpoint: string,
  payload: IngestPayload,
  fetchFn?: typeof window.fetch
): Promise<boolean> {
  const doFetch = fetchFn || window.fetch;
  if (typeof doFetch !== 'function') {
    return false;
  }

  try {
    const data = JSON.stringify(payload);

    const response = await doFetch.call(window, endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'text/plain', // Avoid CORS preflight
      },
      body: data,
      keepalive: true, // Survive page unload
      mode: 'cors',
      credentials: 'omit', // Don't send cookies
    });

    return response.ok;
  } catch {
    return false;
  }
}
