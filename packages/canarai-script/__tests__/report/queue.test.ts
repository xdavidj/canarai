import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { ReportQueue, FlushHandler } from '../../src/report/queue';
import { makeIngestPayload } from '../helpers';

describe('ReportQueue', () => {
  let handler: ReturnType<typeof vi.fn>;
  let queue: ReportQueue;

  beforeEach(() => {
    vi.useFakeTimers();
    handler = vi.fn();
    queue = new ReportQueue(handler);
  });

  afterEach(() => {
    try { queue.stop(); } catch { /* ignore */ }
    vi.useRealTimers();
  });

  it('enqueue adds to queue', () => {
    queue.enqueue(makeIngestPayload());
    expect(queue.size).toBe(1);
  });

  it('flush calls handler with all queued payloads', () => {
    const p1 = makeIngestPayload({ visit_id: 'v1' });
    const p2 = makeIngestPayload({ visit_id: 'v2' });

    queue.enqueue(p1);
    queue.enqueue(p2);
    queue.flush();

    expect(handler).toHaveBeenCalledTimes(1);
    expect(handler).toHaveBeenCalledWith([p1, p2]);
    expect(queue.size).toBe(0);
  });

  it('capacity is MAX_QUEUE_SIZE (50), 51st drops oldest', () => {
    for (let i = 0; i < 51; i++) {
      queue.enqueue(makeIngestPayload({ visit_id: `v${i}` }));
    }

    expect(queue.size).toBe(50);

    queue.flush();
    const payloads = handler.mock.calls[0][0];
    // The first payload (v0) should have been dropped
    expect(payloads[0].visit_id).toBe('v1');
    expect(payloads[payloads.length - 1].visit_id).toBe('v50');
  });

  it('periodic flush every 5 seconds', () => {
    queue.start();
    queue.enqueue(makeIngestPayload());

    expect(handler).not.toHaveBeenCalled();

    vi.advanceTimersByTime(5000);
    expect(handler).toHaveBeenCalledTimes(1);
  });

  it('multiple periodic flushes fire at intervals', () => {
    queue.start();

    queue.enqueue(makeIngestPayload({ visit_id: 'batch1' }));
    vi.advanceTimersByTime(5000);
    expect(handler).toHaveBeenCalledTimes(1);

    queue.enqueue(makeIngestPayload({ visit_id: 'batch2' }));
    vi.advanceTimersByTime(5000);
    expect(handler).toHaveBeenCalledTimes(2);
  });

  it('retry: if flush handler throws, entries re-enqueued with retry+1', () => {
    handler.mockImplementationOnce(() => {
      throw new Error('Flush failed');
    });

    queue.enqueue(makeIngestPayload());
    queue.flush();

    // Entry should be re-enqueued
    expect(queue.size).toBe(1);
  });

  it('retry: entries dropped after 3 retries', () => {
    handler.mockImplementation(() => {
      throw new Error('Flush failed');
    });

    queue.enqueue(makeIngestPayload());

    // Retry 1
    queue.flush();
    expect(queue.size).toBe(1);

    // Retry 2
    queue.flush();
    expect(queue.size).toBe(1);

    // Retry 3 — should be dropped (retries = 3 >= MAX_RETRIES)
    queue.flush();
    expect(queue.size).toBe(0);
  });

  it('visibilitychange to hidden triggers flush', () => {
    queue.start();
    queue.enqueue(makeIngestPayload());

    // Simulate visibilitychange to hidden
    Object.defineProperty(document, 'visibilityState', {
      value: 'hidden',
      writable: true,
      configurable: true,
    });
    document.dispatchEvent(new Event('visibilitychange'));

    expect(handler).toHaveBeenCalledTimes(1);

    // Restore
    Object.defineProperty(document, 'visibilityState', {
      value: 'visible',
      writable: true,
      configurable: true,
    });
  });

  it('beforeunload triggers flush', () => {
    queue.start();
    queue.enqueue(makeIngestPayload());

    window.dispatchEvent(new Event('beforeunload'));

    expect(handler).toHaveBeenCalledTimes(1);
  });

  it('pagehide triggers flush', () => {
    queue.start();
    queue.enqueue(makeIngestPayload());

    window.dispatchEvent(new Event('pagehide'));

    expect(handler).toHaveBeenCalledTimes(1);
  });

  it('stop clears interval, removes listeners, does final flush', () => {
    queue.start();
    queue.enqueue(makeIngestPayload());

    queue.stop();

    // Final flush should have been called
    expect(handler).toHaveBeenCalledTimes(1);
    expect(queue.size).toBe(0);

    // After stop, periodic flush should not fire
    handler.mockClear();
    queue.enqueue(makeIngestPayload());
    vi.advanceTimersByTime(10000);
    // No more periodic flushes
    expect(handler).not.toHaveBeenCalled();
  });

  it('size getter returns queue length', () => {
    expect(queue.size).toBe(0);
    queue.enqueue(makeIngestPayload());
    expect(queue.size).toBe(1);
    queue.enqueue(makeIngestPayload());
    expect(queue.size).toBe(2);
    queue.flush();
    expect(queue.size).toBe(0);
  });

  it('flush does nothing when queue is empty', () => {
    queue.flush();
    expect(handler).not.toHaveBeenCalled();
  });

  it('stop removes beforeunload listener', () => {
    queue.start();
    queue.stop();
    handler.mockClear();

    queue.enqueue(makeIngestPayload());
    window.dispatchEvent(new Event('beforeunload'));

    // Listener removed — should not flush
    expect(handler).not.toHaveBeenCalled();
  });

  it('stop removes visibilitychange listener', () => {
    queue.start();
    queue.stop();
    handler.mockClear();

    queue.enqueue(makeIngestPayload());
    Object.defineProperty(document, 'visibilityState', {
      value: 'hidden',
      writable: true,
      configurable: true,
    });
    document.dispatchEvent(new Event('visibilitychange'));

    expect(handler).not.toHaveBeenCalled();

    Object.defineProperty(document, 'visibilityState', {
      value: 'visible',
      writable: true,
      configurable: true,
    });
  });
});
