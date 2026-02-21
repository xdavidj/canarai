/**
 * Batching queue.
 * Collects report payloads and flushes them periodically or on page unload.
 * Ensures data is sent even if the user navigates away.
 */

import type { IngestPayload } from '../types';

/** Default flush interval: 5 seconds */
const FLUSH_INTERVAL_MS = 5_000;

/**
 * SECURITY (M-2): Cap queue size to prevent unbounded memory growth.
 * If an agent triggers many reports and the network is slow/unavailable,
 * an unbounded queue could exhaust browser memory.
 */
const MAX_QUEUE_SIZE = 50;

/**
 * SECURITY (M-2): Cap retries to prevent infinite re-enqueue loops.
 * After MAX_RETRIES failed flush attempts, payloads are dropped.
 */
const MAX_RETRIES = 3;

export type FlushHandler = (payloads: IngestPayload[]) => void;

/** Wrapper to track retry count per payload */
interface QueueEntry {
  payload: IngestPayload;
  retries: number;
}

export class ReportQueue {
  private queue: QueueEntry[] = [];
  private flushHandler: FlushHandler;
  private flushTimer: ReturnType<typeof setInterval> | null = null;
  private bound_onVisibilityChange: () => void;
  private bound_onBeforeUnload: () => void;

  constructor(flushHandler: FlushHandler) {
    this.flushHandler = flushHandler;
    this.bound_onVisibilityChange = this.onVisibilityChange.bind(this);
    this.bound_onBeforeUnload = this.onBeforeUnload.bind(this);
  }

  /**
   * Start the queue — begins periodic flushing and listens for page unload.
   */
  start(): void {
    // Periodic flush
    this.flushTimer = setInterval(() => {
      this.flush();
    }, FLUSH_INTERVAL_MS);

    // Flush on page hide/unload
    document.addEventListener('visibilitychange', this.bound_onVisibilityChange);
    window.addEventListener('beforeunload', this.bound_onBeforeUnload);

    // pagehide is more reliable than beforeunload on mobile
    window.addEventListener('pagehide', this.bound_onBeforeUnload);
  }

  /**
   * Add a payload to the queue.
   * SECURITY (M-2): If the queue is at capacity, drop the oldest entry
   * to prevent unbounded memory growth.
   */
  enqueue(payload: IngestPayload): void {
    if (this.queue.length >= MAX_QUEUE_SIZE) {
      // Drop the oldest entry to make room
      this.queue.shift();
    }
    this.queue.push({ payload, retries: 0 });
  }

  /**
   * Flush all queued payloads immediately.
   * SECURITY (M-2): Track retry count per payload. After MAX_RETRIES
   * failed attempts, the payload is permanently dropped to prevent
   * infinite re-enqueue loops and unbounded growth.
   */
  flush(): void {
    if (this.queue.length === 0) return;

    const entries = this.queue.splice(0);
    const payloads = entries.map(e => e.payload);
    try {
      this.flushHandler(payloads);
    } catch {
      // Re-enqueue entries that haven't exceeded max retries
      const retriable = entries
        .map(e => ({ payload: e.payload, retries: e.retries + 1 }))
        .filter(e => e.retries < MAX_RETRIES);

      // Only re-enqueue up to the remaining capacity
      const capacity = MAX_QUEUE_SIZE - this.queue.length;
      if (retriable.length > 0 && capacity > 0) {
        this.queue.unshift(...retriable.slice(0, capacity));
      }
    }
  }

  /**
   * Stop the queue and clean up.
   */
  stop(): void {
    if (this.flushTimer !== null) {
      clearInterval(this.flushTimer);
      this.flushTimer = null;
    }

    document.removeEventListener('visibilitychange', this.bound_onVisibilityChange);
    window.removeEventListener('beforeunload', this.bound_onBeforeUnload);
    window.removeEventListener('pagehide', this.bound_onBeforeUnload);

    // Final flush
    this.flush();
  }

  /**
   * Get the current queue size.
   */
  get size(): number {
    return this.queue.length;
  }

  private onVisibilityChange(): void {
    if (document.visibilityState === 'hidden') {
      this.flush();
    }
  }

  private onBeforeUnload(): void {
    this.flush();
  }
}
