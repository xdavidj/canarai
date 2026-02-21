import { describe, it, expect, vi, beforeEach } from 'vitest';
import { TimingTracker, createTimingTracker } from '../../src/observe/timing';

describe('TimingTracker', () => {
  let tracker: TimingTracker;

  beforeEach(() => {
    vi.spyOn(performance, 'now').mockReturnValue(1000);
    tracker = new TimingTracker(['test-1', 'test-2', 'test-3']);
  });

  it('creates records for all test IDs with injectedAt set', () => {
    const all = tracker.getAll();
    expect(all).toHaveLength(3);
    for (const record of all) {
      expect(record.injectedAt).toBe(1000);
      expect(record.firstResponseAt).toBeNull();
      expect(record.lastResponseAt).toBeNull();
      expect(record.responseCount).toBe(0);
    }
  });

  it('markInjection updates injectedAt timestamp', () => {
    vi.spyOn(performance, 'now').mockReturnValue(2000);
    tracker.markInjection('test-1');
    const record = tracker.get('test-1');
    expect(record?.injectedAt).toBe(2000);
  });

  it('markResponse sets firstResponseAt on first call', () => {
    vi.spyOn(performance, 'now').mockReturnValue(1500);
    tracker.markResponse('test-1');
    const record = tracker.get('test-1');
    expect(record?.firstResponseAt).toBe(1500);
    expect(record?.lastResponseAt).toBe(1500);
    expect(record?.responseCount).toBe(1);
  });

  it('markResponse updates lastResponseAt on subsequent calls', () => {
    vi.spyOn(performance, 'now').mockReturnValue(1500);
    tracker.markResponse('test-1');

    vi.spyOn(performance, 'now').mockReturnValue(2500);
    tracker.markResponse('test-1');

    const record = tracker.get('test-1');
    expect(record?.firstResponseAt).toBe(1500);
    expect(record?.lastResponseAt).toBe(2500);
    expect(record?.responseCount).toBe(2);
  });

  it('getResponseTimeMs returns firstResponseAt - injectedAt', () => {
    vi.spyOn(performance, 'now').mockReturnValue(1500);
    tracker.markResponse('test-1');
    expect(tracker.getResponseTimeMs('test-1')).toBe(500); // 1500 - 1000
  });

  it('getResponseTimeMs returns null if no response', () => {
    expect(tracker.getResponseTimeMs('test-1')).toBeNull();
  });

  it('markResponse is a no-op for unknown testId', () => {
    tracker.markResponse('unknown-id');
    expect(tracker.get('unknown-id')).toBeUndefined();
  });

  it('getResponseTimeMs returns null for unknown testId', () => {
    // get() returns undefined for unknown testId, then the function
    // checks !record which is true, so returns null
    expect(tracker.getResponseTimeMs('unknown-id')).toBeNull();
  });

  it('getAll returns all records', () => {
    const all = tracker.getAll();
    expect(all).toHaveLength(3);
    const ids = all.map(r => r.testId);
    expect(ids).toContain('test-1');
    expect(ids).toContain('test-2');
    expect(ids).toContain('test-3');
  });

  it('get returns specific record', () => {
    const record = tracker.get('test-2');
    expect(record).toBeDefined();
    expect(record?.testId).toBe('test-2');
  });

  it('get returns undefined for unknown testId', () => {
    expect(tracker.get('nonexistent')).toBeUndefined();
  });

  it('multiple responses increment responseCount correctly', () => {
    vi.spyOn(performance, 'now').mockReturnValue(1100);
    tracker.markResponse('test-1');
    vi.spyOn(performance, 'now').mockReturnValue(1200);
    tracker.markResponse('test-1');
    vi.spyOn(performance, 'now').mockReturnValue(1300);
    tracker.markResponse('test-1');

    const record = tracker.get('test-1');
    expect(record?.responseCount).toBe(3);
    expect(record?.firstResponseAt).toBe(1100);
    expect(record?.lastResponseAt).toBe(1300);
  });
});

describe('createTimingTracker', () => {
  it('returns a TimingTracker instance', () => {
    const tracker = createTimingTracker(['a', 'b']);
    expect(tracker).toBeInstanceOf(TimingTracker);
    expect(tracker.getAll()).toHaveLength(2);
  });
});
