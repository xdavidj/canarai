import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { sendPixel } from '../../src/report/pixel';
import { makeIngestPayload } from '../helpers';

describe('sendPixel', () => {
  const endpoint = 'https://api.canar.ai/v1/ingest';

  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('creates an Image element appended to document.body', () => {
    const payload = makeIngestPayload();
    sendPixel(endpoint, payload);

    const img = document.body.querySelector('img');
    expect(img).not.toBeNull();
  });

  it('image src contains URL params including v, sk, vid, ts, url, conf, cls', () => {
    const payload = makeIngestPayload({
      v: 1,
      site_key: 'ca_live_test',
      visit_id: 'visit-123',
      timestamp: '2026-02-21T00:00:00Z',
      page_url: 'https://example.com/page',
    });

    sendPixel(endpoint, payload);

    const img = document.body.querySelector('img');
    expect(img).not.toBeNull();
    const src = img!.getAttribute('src') || '';
    expect(src).toContain('v=1');
    expect(src).toContain('sk=ca_live_test');
    expect(src).toContain('vid=visit-123');
    expect(src).toContain('ts=');
    expect(src).toContain('url=');
    expect(src).toContain('conf=');
    expect(src).toContain('cls=');
  });

  it('URL is truncated to 2000 chars', () => {
    const payload = makeIngestPayload({
      page_url: 'https://example.com/' + 'x'.repeat(3000),
    });

    sendPixel(endpoint, payload);

    const img = document.body.querySelector('img');
    expect(img).not.toBeNull();
    const src = img!.getAttribute('src') || '';
    expect(src.length).toBeLessThanOrEqual(2000);
  });

  it('abbreviates exfiltration_attempted to ex', () => {
    const payload = makeIngestPayload({
      test_results: [
        {
          test_id: 'CAN-0001',
          test_version: '1.0.0',
          delivery_method: 'css_display_none',
          outcome: 'exfiltration_attempted',
          evidence: {},
        },
      ],
    });

    sendPixel(endpoint, payload);

    const img = document.body.querySelector('img');
    const src = img!.getAttribute('src') || '';
    expect(src).toContain('CAN-0001');
    // URL encodes : as %3A
    expect(src).toContain('CAN-0001%3Aex');
  });

  it('abbreviates full_compliance to fc', () => {
    const payload = makeIngestPayload({
      test_results: [
        {
          test_id: 'CAN-0002',
          test_version: '1.0.0',
          delivery_method: 'meta_tag',
          outcome: 'full_compliance',
          evidence: {},
        },
      ],
    });

    sendPixel(endpoint, payload);

    const img = document.body.querySelector('img');
    const src = img!.getAttribute('src') || '';
    // URL encodes : as %3A
    expect(src).toContain('%3Afc');
  });

  it('abbreviates partial_compliance to pc, acknowledged to ak, ignored to ig', () => {
    const payload = makeIngestPayload({
      test_results: [
        { test_id: 'CAN-0003', test_version: '1.0.0', delivery_method: 'a', outcome: 'partial_compliance', evidence: {} },
        { test_id: 'CAN-0004', test_version: '1.0.0', delivery_method: 'b', outcome: 'acknowledged', evidence: {} },
        { test_id: 'CAN-0005', test_version: '1.0.0', delivery_method: 'c', outcome: 'ignored', evidence: {} },
      ],
    });

    sendPixel(endpoint, payload);

    const img = document.body.querySelector('img');
    const src = img!.getAttribute('src') || '';
    // URL encodes : as %3A
    expect(src).toContain('%3Apc');
    expect(src).toContain('%3Aak');
    expect(src).toContain('%3Aig');
  });

  it('returns true on success', () => {
    const result = sendPixel(endpoint, makeIngestPayload());
    expect(result).toBe(true);
  });

  it('image is removed after timeout', () => {
    sendPixel(endpoint, makeIngestPayload());

    const imgBefore = document.body.querySelector('img');
    expect(imgBefore).not.toBeNull();

    vi.advanceTimersByTime(5000);

    const imgAfter = document.body.querySelector('img');
    expect(imgAfter).toBeNull();
  });

  it('image has aria-hidden="true"', () => {
    sendPixel(endpoint, makeIngestPayload());

    const img = document.body.querySelector('img');
    expect(img).not.toBeNull();
    expect(img!.getAttribute('aria-hidden')).toBe('true');
  });

  it('image is positioned offscreen', () => {
    sendPixel(endpoint, makeIngestPayload());

    const img = document.body.querySelector('img') as HTMLImageElement;
    expect(img.style.position).toBe('absolute');
    expect(img.style.left).toBe('-9999px');
    expect(img.style.top).toBe('-9999px');
  });
});
