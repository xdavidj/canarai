/**
 * DOM Mutation Observer.
 * Watches for DOM changes that reference canary markers, indicating
 * an AI agent has read and is responding to injected test content.
 */

export interface MutationEvent {
  type: 'childList' | 'characterData' | 'attributes';
  timestamp: number;
  targetSelector: string;
  detail: string;
  matchedMarker?: string;
}

/**
 * Start observing DOM mutations for canary marker references.
 *
 * @param markers - Canary token strings to watch for
 * @param onEvent - Callback fired when a relevant mutation is detected
 * @returns Cleanup function to disconnect the observer
 */
export function observeMutations(
  markers: string[],
  onEvent: (event: MutationEvent) => void
): () => void {
  if (markers.length === 0 || typeof MutationObserver === 'undefined') {
    return () => {};
  }

  // Build a set for O(1) lookups and a combined regex for content scanning
  const markerSet = new Set(markers);
  const markerPattern = new RegExp(
    markers.map(m => m.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|'),
    'i'
  );

  /**
   * Check if a string contains any canary marker.
   */
  function findMarker(text: string): string | undefined {
    if (!text) return undefined;
    for (const marker of markerSet) {
      if (text.includes(marker)) return marker;
    }
    return undefined;
  }

  /**
   * Get a simple selector string for an element (for logging).
   */
  function getSelector(node: Node): string {
    if (node instanceof Element) {
      const tag = node.tagName.toLowerCase();
      const id = node.id ? `#${node.id}` : '';
      const cls = node.className && typeof node.className === 'string'
        ? '.' + node.className.trim().split(/\s+/).slice(0, 2).join('.')
        : '';
      return `${tag}${id}${cls}`;
    }
    return node.nodeName;
  }

  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      const timestamp = performance.now();
      const targetSelector = getSelector(mutation.target);

      // Check added nodes
      if (mutation.type === 'childList') {
        mutation.addedNodes.forEach(node => {
          const text = node.textContent || '';
          const marker = findMarker(text);

          // Also check element attributes
          let attrMarker: string | undefined;
          if (node instanceof Element) {
            for (const attr of Array.from(node.attributes)) {
              attrMarker = findMarker(attr.value);
              if (attrMarker) break;
            }

            // Check for src/href attributes that may contain markers (exfil vectors)
            const src = node.getAttribute('src') || '';
            const href = node.getAttribute('href') || '';
            if (!attrMarker) attrMarker = findMarker(src) || findMarker(href);
          }

          const matched = marker || attrMarker;
          if (matched || markerPattern.test(node.textContent || '')) {
            onEvent({
              type: 'childList',
              timestamp,
              targetSelector: getSelector(node),
              detail: `Node added: ${getSelector(node)}`,
              matchedMarker: matched,
            });
          }
        });
      }

      // Check character data changes
      if (mutation.type === 'characterData') {
        const text = mutation.target.textContent || '';
        const marker = findMarker(text);
        if (marker) {
          onEvent({
            type: 'characterData',
            timestamp,
            targetSelector,
            detail: `Text changed in ${targetSelector}`,
            matchedMarker: marker,
          });
        }
      }

      // Check attribute changes
      if (mutation.type === 'attributes' && mutation.target instanceof Element) {
        const attrName = mutation.attributeName || '';
        const attrValue = mutation.target.getAttribute(attrName) || '';
        const marker = findMarker(attrValue);
        if (marker) {
          onEvent({
            type: 'attributes',
            timestamp,
            targetSelector,
            detail: `Attribute "${attrName}" changed on ${targetSelector}`,
            matchedMarker: marker,
          });
        }
      }
    }
  });

  observer.observe(document.documentElement, {
    childList: true,
    subtree: true,
    characterData: true,
    attributes: true,
    // SECURITY (M-3): 'data-*' is not a valid attributeFilter value.
    // MutationObserver attributeFilter requires exact attribute names.
    // Wildcards are silently ignored, meaning data attribute changes were
    // not being observed at all. List the specific data attributes we need.
    attributeFilter: ['src', 'href', 'content', 'value', 'data-canary-instruction', 'data-canary-test'],
  });

  return () => observer.disconnect();
}
