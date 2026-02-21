import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { sendBeacon } from '../../src/report/beacon';
import { makeIngestPayload } from '../helpers';

describe('sendBeacon', () => {
  const endpoint = 'https://api.canar.ai/v1/ingest';
  let originalSendBeacon: typeof navigator.sendBeacon;

  beforeEach(() => {
    originalSendBeacon = navigator.sendBeacon;
  });

  afterEach(() => {
    // Restore
    Object.defineProperty(navigator, 'sendBeacon', {
      value: originalSendBeacon,
      writable: true,
      configurable: true,
    });
  });

  it('uses navigator.sendBeacon with Blob of type text/plain', () => {
    const mockSendBeacon = vi.fn().mockReturnValue(true);
    Object.defineProperty(navigator, 'sendBeacon', {
      value: mockSendBeacon,
      writable: true,
      configurable: true,
    });

    const payload = makeIngestPayload();
    sendBeacon(endpoint, payload);

    expect(mockSendBeacon).toHaveBeenCalledTimes(1);
    const [url, blob] = mockSendBeacon.mock.calls[0];
    expect(url).toBe(endpoint);
    expect(blob).toBeInstanceOf(Blob);
    expect(blob.type).toBe('text/plain');
  });

  it('returns true when sendBeacon succeeds', () => {
    Object.defineProperty(navigator, 'sendBeacon', {
      value: vi.fn().mockReturnValue(true),
      writable: true,
      configurable: true,
    });

    const result = sendBeacon(endpoint, makeIngestPayload());
    expect(result).toBe(true);
  });

  it('returns false when sendBeacon is unavailable', () => {
    Object.defineProperty(navigator, 'sendBeacon', {
      value: undefined,
      writable: true,
      configurable: true,
    });

    const result = sendBeacon(endpoint, makeIngestPayload());
    expect(result).toBe(false);
  });

  it('returns false when sendBeacon throws', () => {
    Object.defineProperty(navigator, 'sendBeacon', {
      value: vi.fn().mockImplementation(() => {
        throw new Error('sendBeacon error');
      }),
      writable: true,
      configurable: true,
    });

    const result = sendBeacon(endpoint, makeIngestPayload());
    expect(result).toBe(false);
  });

  it('returns false when sendBeacon returns false', () => {
    Object.defineProperty(navigator, 'sendBeacon', {
      value: vi.fn().mockReturnValue(false),
      writable: true,
      configurable: true,
    });

    const result = sendBeacon(endpoint, makeIngestPayload());
    expect(result).toBe(false);
  });

  it('Blob contains JSON.stringify of payload', () => {
    const mockSendBeacon = vi.fn().mockReturnValue(true);
    Object.defineProperty(navigator, 'sendBeacon', {
      value: mockSendBeacon,
      writable: true,
      configurable: true,
    });

    const payload = makeIngestPayload();
    sendBeacon(endpoint, payload);

    const blob: Blob = mockSendBeacon.mock.calls[0][1];
    expect(blob).toBeInstanceOf(Blob);
    expect(blob.size).toBe(JSON.stringify(payload).length);
  });

  it('payload is serialized correctly with all fields', () => {
    const mockSendBeacon = vi.fn().mockReturnValue(true);
    Object.defineProperty(navigator, 'sendBeacon', {
      value: mockSendBeacon,
      writable: true,
      configurable: true,
    });

    const payload = makeIngestPayload({
      site_key: 'ca_live_abc123',
      visit_id: 'visit-xyz',
      test_results: [
        {
          test_id: 'CAN-0001',
          test_version: '1.0.0',
          delivery_method: 'css_display_none',
          outcome: 'ignored',
          evidence: { canaraiTokenObserved: false },
        },
      ],
    });

    sendBeacon(endpoint, payload);

    const blob: Blob = mockSendBeacon.mock.calls[0][1];
    expect(blob.size).toBeGreaterThan(0);
    // Verify size matches the expected JSON serialization
    expect(blob.size).toBe(JSON.stringify(payload).length);
  });

  it('sends to the correct endpoint URL', () => {
    const mockSendBeacon = vi.fn().mockReturnValue(true);
    Object.defineProperty(navigator, 'sendBeacon', {
      value: mockSendBeacon,
      writable: true,
      configurable: true,
    });

    const customEndpoint = 'https://custom.canar.ai/v1/ingest';
    sendBeacon(customEndpoint, makeIngestPayload());

    expect(mockSendBeacon.mock.calls[0][0]).toBe(customEndpoint);
  });
});
