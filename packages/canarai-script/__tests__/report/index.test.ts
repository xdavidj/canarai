import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import type { IngestPayload, CanaraiConfig } from '../../src/types';
import { makeIngestPayload } from '../helpers';

// Mock the sub-modules
vi.mock('../../src/report/beacon', () => ({
  sendBeacon: vi.fn().mockReturnValue(true),
}));

vi.mock('../../src/report/fetch', () => ({
  sendFetch: vi.fn().mockResolvedValue(true),
}));

vi.mock('../../src/report/pixel', () => ({
  sendPixel: vi.fn().mockReturnValue(true),
}));

import { createReporter } from '../../src/report/index';
import { sendBeacon } from '../../src/report/beacon';
import { sendFetch } from '../../src/report/fetch';
import { sendPixel } from '../../src/report/pixel';

describe('createReporter', () => {
  let config: CanaraiConfig;

  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();

    config = {
      siteKey: 'ca_live_test',
      endpoint: 'https://api.canar.ai/v1/ingest',
      reportingMode: 'beacon',
      debug: false,
    };
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('default mode (beacon): tries beacon first', () => {
    const reporter = createReporter(config);
    const payload = makeIngestPayload();

    reporter.report(payload);
    reporter.flush();

    expect(sendBeacon).toHaveBeenCalled();
    reporter.shutdown();
  });

  it('beacon mode: falls back to fetch then pixel if beacon fails', () => {
    vi.mocked(sendBeacon).mockReturnValue(false);
    vi.mocked(sendFetch).mockResolvedValue(false);

    const reporter = createReporter(config);
    const payload = makeIngestPayload();

    reporter.report(payload);
    reporter.flush();

    expect(sendBeacon).toHaveBeenCalled();
    // fetch should be tried as fallback
    expect(sendFetch).toHaveBeenCalled();
    reporter.shutdown();
  });

  it('fetch mode: tries fetch first', async () => {
    config.reportingMode = 'fetch';
    const reporter = createReporter(config);
    const payload = makeIngestPayload();

    reporter.report(payload);
    reporter.flush();

    expect(sendFetch).toHaveBeenCalled();
    reporter.shutdown();
  });

  it('pixel mode: goes straight to pixel', () => {
    config.reportingMode = 'pixel';
    const reporter = createReporter(config);
    const payload = makeIngestPayload();

    reporter.report(payload);
    reporter.flush();

    expect(sendPixel).toHaveBeenCalled();
    reporter.shutdown();
  });

  it('reporter.report() enqueues payload', () => {
    const reporter = createReporter(config);
    const payload = makeIngestPayload();

    reporter.report(payload);
    // Should not have sent yet (in queue)
    expect(sendBeacon).not.toHaveBeenCalled();
    reporter.shutdown();
  });

  it('reporter.flush() triggers immediate flush', () => {
    const reporter = createReporter(config);
    const payload = makeIngestPayload();

    reporter.report(payload);
    reporter.flush();

    expect(sendBeacon).toHaveBeenCalled();
    reporter.shutdown();
  });

  it('reporter.shutdown() stops queue and flushes remaining', () => {
    const reporter = createReporter(config);
    const payload = makeIngestPayload();

    reporter.report(payload);
    reporter.shutdown();

    // Final flush should have been called
    expect(sendBeacon).toHaveBeenCalled();
  });

  it('passes custom fetchFn to sendFetch', () => {
    config.reportingMode = 'fetch';
    const customFetch = vi.fn().mockResolvedValue(new Response('ok'));
    const reporter = createReporter(config, customFetch);
    const payload = makeIngestPayload();

    reporter.report(payload);
    reporter.flush();

    expect(sendFetch).toHaveBeenCalledWith(
      config.endpoint,
      payload,
      customFetch
    );
    reporter.shutdown();
  });

  it('periodic flush sends queued payloads after 5 seconds', () => {
    const reporter = createReporter(config);
    const payload = makeIngestPayload();

    reporter.report(payload);

    vi.advanceTimersByTime(5000);

    expect(sendBeacon).toHaveBeenCalled();
    reporter.shutdown();
  });

  it('multiple payloads are all flushed', () => {
    const reporter = createReporter(config);

    reporter.report(makeIngestPayload({ visit_id: 'v1' }));
    reporter.report(makeIngestPayload({ visit_id: 'v2' }));
    reporter.report(makeIngestPayload({ visit_id: 'v3' }));
    reporter.flush();

    expect(sendBeacon).toHaveBeenCalledTimes(3);
    reporter.shutdown();
  });
});
