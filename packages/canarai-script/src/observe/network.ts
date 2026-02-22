/**
 * Network Observer.
 * Monitors outbound requests by patching fetch and XMLHttpRequest,
 * and watching for dynamically created img/script/iframe elements.
 * Looks for canary markers in URLs and request bodies.
 */

export interface NetworkEvent {
  type: 'fetch' | 'xhr' | 'element';
  timestamp: number;
  url: string;
  method?: string;
  matchedMarker?: string;
  body?: string;
}

/**
 * Start monitoring outbound network requests for canary marker exfiltration.
 *
 * @param markers - canar.ai token strings to watch for
 * @param onEvent - Callback fired when a relevant network request is detected
 * @returns Cleanup function to restore original APIs and stop observation
 */
export function observeNetwork(
  markers: string[],
  onEvent: (event: NetworkEvent) => void
): () => void {
  if (markers.length === 0) return () => {};

  const cleanups: Array<() => void> = [];

  /**
   * SECURITY (H-4): Use a WeakMap instead of direct property assignment on
   * XMLHttpRequest instances. Direct properties like this._canaryUrl are
   * visible and modifiable by any code with a reference to the XHR object,
   * which could be exploited to spoof or suppress canary marker detection.
   * A WeakMap is not enumerable and cannot be accessed without the map reference.
   */
  const xhrMeta = new WeakMap<XMLHttpRequest, { url: string; method: string }>();

  /**
   * Check if a string contains any canary marker.
   */
  function findMarker(text: string): string | undefined {
    if (!text) return undefined;
    for (const marker of markers) {
      if (text.includes(marker)) return marker;
    }
    return undefined;
  }

  // ── Patch fetch ──
  const originalFetch = window.fetch;
  if (typeof originalFetch === 'function') {
    window.fetch = function patchedFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
      try {
        const url = typeof input === 'string' ? input :
                     input instanceof URL ? input.toString() :
                     input.url;
        const method = init?.method || 'GET';
        const body = init?.body ? String(init.body) : '';

        const urlMarker = findMarker(url);
        const bodyMarker = findMarker(body);

        if (urlMarker || bodyMarker) {
          onEvent({
            type: 'fetch',
            timestamp: performance.now(),
            url,
            method,
            matchedMarker: urlMarker || bodyMarker,
            body: body.slice(0, 500),
          });
        }
      } catch {
        // Don't break the page if our monitoring fails
      }

      return originalFetch.apply(window, [input, init] as unknown as Parameters<typeof fetch>);
    };

    cleanups.push(() => { window.fetch = originalFetch; });
  }

  // ── Patch XMLHttpRequest.open ──
  const originalXHROpen = XMLHttpRequest.prototype.open;
  const originalXHRSend = XMLHttpRequest.prototype.send;

  XMLHttpRequest.prototype.open = function(
    method: string,
    url: string | URL,
    ...rest: unknown[]
  ): void {
    // Store URL and method in WeakMap keyed by the XHR instance
    xhrMeta.set(this, { url: String(url), method });
    return originalXHROpen.apply(this, [method, url, ...rest] as unknown as Parameters<typeof originalXHROpen>);
  };

  XMLHttpRequest.prototype.send = function(body?: Document | XMLHttpRequestBodyInit | null): void {
    try {
      const meta = xhrMeta.get(this);
      const url = meta?.url || '';
      const method = meta?.method || 'GET';
      const bodyStr = body ? String(body) : '';

      const urlMarker = findMarker(url);
      const bodyMarker = findMarker(bodyStr);

      if (urlMarker || bodyMarker) {
        onEvent({
          type: 'xhr',
          timestamp: performance.now(),
          url,
          method,
          matchedMarker: urlMarker || bodyMarker,
          body: bodyStr.slice(0, 500),
        });
      }
    } catch {
      // Don't break the page
    }

    return originalXHRSend.apply(this, [body] as unknown as Parameters<typeof originalXHRSend>);
  };

  cleanups.push(() => {
    XMLHttpRequest.prototype.open = originalXHROpen;
    XMLHttpRequest.prototype.send = originalXHRSend;
  });

  // ── Watch for new img/script/iframe elements (exfil vectors) ──
  let elementObserver: MutationObserver | null = null;
  if (typeof MutationObserver !== 'undefined') {
    elementObserver = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        mutation.addedNodes.forEach(node => {
          if (!(node instanceof HTMLElement)) return;

          const checkElement = (el: HTMLElement) => {
            const tag = el.tagName.toLowerCase();
            if (tag !== 'img' && tag !== 'script' && tag !== 'iframe') return;

            const src = el.getAttribute('src') || '';
            const marker = findMarker(src);
            if (marker) {
              onEvent({
                type: 'element',
                timestamp: performance.now(),
                url: src,
                matchedMarker: marker,
              });
            }
          };

          checkElement(node);
          // Also check child elements (e.g., a wrapper div containing an img)
          node.querySelectorAll('img, script, iframe').forEach(child => {
            checkElement(child as HTMLElement);
          });
        });
      }
    });

    elementObserver.observe(document.documentElement, {
      childList: true,
      subtree: true,
    });

    cleanups.push(() => { elementObserver?.disconnect(); });
  }

  return () => {
    for (const cleanup of cleanups) {
      try { cleanup(); } catch { /* ignore */ }
    }
  };
}
