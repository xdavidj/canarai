/**
 * Reporter orchestrator.
 * Manages sending ingest payloads to the API using the best available method.
 * Priority: beacon > fetch > pixel
 * Uses a batching queue for efficient delivery.
 */

import type { CanaryConfig, IngestPayload } from '../types';
import { sendBeacon } from './beacon';
import { sendFetch } from './fetch';
import { sendPixel } from './pixel';
import { ReportQueue } from './queue';

/**
 * Send a single payload using the best available method.
 * SECURITY (M-5/M-6): Accepts fetchFn to use the native fetch reference.
 */
function sendPayload(
  endpoint: string,
  payload: IngestPayload,
  preferredMode: CanaryConfig['reportingMode'],
  fetchFn?: typeof window.fetch
): void {
  // Try preferred mode first, then fall back
  if (preferredMode === 'beacon' || !preferredMode) {
    if (sendBeacon(endpoint, payload)) return;
    // Fallback to fetch
    sendFetch(endpoint, payload, fetchFn).catch(() => {
      // Last resort: pixel
      sendPixel(endpoint, payload);
    });
    return;
  }

  if (preferredMode === 'fetch') {
    sendFetch(endpoint, payload, fetchFn).then(ok => {
      if (!ok) {
        if (!sendBeacon(endpoint, payload)) {
          sendPixel(endpoint, payload);
        }
      }
    }).catch(() => {
      if (!sendBeacon(endpoint, payload)) {
        sendPixel(endpoint, payload);
      }
    });
    return;
  }

  if (preferredMode === 'pixel') {
    sendPixel(endpoint, payload);
    return;
  }

  // Unknown mode, try beacon
  if (!sendBeacon(endpoint, payload)) {
    sendFetch(endpoint, payload, fetchFn).catch(() => {
      sendPixel(endpoint, payload);
    });
  }
}

/**
 * Create a reporter instance tied to a specific config.
 * Returns an object with enqueue/flush methods backed by a batching queue.
 *
 * SECURITY (M-5/M-6): Accepts an optional fetchFn parameter (the native fetch
 * captured at module load) to avoid sending reports through monkey-patched fetch.
 */
export function createReporter(config: CanaryConfig, fetchFn?: typeof window.fetch) {
  const queue = new ReportQueue((payloads: IngestPayload[]) => {
    for (const payload of payloads) {
      sendPayload(config.endpoint, payload, config.reportingMode, fetchFn);
    }
  });

  queue.start();

  return {
    /**
     * Enqueue a payload for batched delivery.
     */
    report(payload: IngestPayload): void {
      queue.enqueue(payload);
    },

    /**
     * Immediately flush all queued payloads.
     */
    flush(): void {
      queue.flush();
    },

    /**
     * Stop the reporter and flush remaining payloads.
     */
    shutdown(): void {
      queue.stop();
    },
  };
}
