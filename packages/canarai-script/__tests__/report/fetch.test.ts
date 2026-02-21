import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { sendFetch } from '../../src/report/fetch';
import { makeIngestPayload } from '../helpers';

describe('sendFetch', () => {
  const endpoint = 'https://api.canar.ai/v1/ingest';
  let mockFetch: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockFetch = vi.fn().mockResolvedValue(new Response('ok', { status: 200 }));
    vi.stubGlobal('fetch', mockFetch);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('uses keepalive: true', async () => {
    await sendFetch(endpoint, makeIngestPayload());

    expect(mockFetch).toHaveBeenCalledWith(
      endpoint,
      expect.objectContaining({
        keepalive: true,
      })
    );
  });

  it('uses credentials: omit', async () => {
    await sendFetch(endpoint, makeIngestPayload());

    expect(mockFetch).toHaveBeenCalledWith(
      endpoint,
      expect.objectContaining({
        credentials: 'omit',
      })
    );
  });

  it('uses Content-Type: text/plain', async () => {
    await sendFetch(endpoint, makeIngestPayload());

    expect(mockFetch).toHaveBeenCalledWith(
      endpoint,
      expect.objectContaining({
        headers: { 'Content-Type': 'text/plain' },
      })
    );
  });

  it('custom fetchFn parameter is used instead of window.fetch', async () => {
    const customFetch = vi.fn().mockResolvedValue(new Response('ok', { status: 200 }));

    await sendFetch(endpoint, makeIngestPayload(), customFetch);

    expect(customFetch).toHaveBeenCalled();
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('returns true on 200 response', async () => {
    const result = await sendFetch(endpoint, makeIngestPayload());
    expect(result).toBe(true);
  });

  it('returns false on non-ok response', async () => {
    mockFetch.mockResolvedValue(new Response('error', { status: 500 }));

    const result = await sendFetch(endpoint, makeIngestPayload());
    expect(result).toBe(false);
  });

  it('returns false on network error', async () => {
    mockFetch.mockRejectedValue(new Error('Network failure'));

    const result = await sendFetch(endpoint, makeIngestPayload());
    expect(result).toBe(false);
  });

  it('returns false when fetch is unavailable', async () => {
    vi.stubGlobal('fetch', undefined);

    const result = await sendFetch(endpoint, makeIngestPayload());
    expect(result).toBe(false);
  });

  it('sends POST method', async () => {
    await sendFetch(endpoint, makeIngestPayload());

    expect(mockFetch).toHaveBeenCalledWith(
      endpoint,
      expect.objectContaining({
        method: 'POST',
      })
    );
  });

  it('body contains JSON stringified payload', async () => {
    const payload = makeIngestPayload();
    await sendFetch(endpoint, payload);

    const callArgs = mockFetch.mock.calls[0][1];
    expect(callArgs.body).toBe(JSON.stringify(payload));
  });
});
