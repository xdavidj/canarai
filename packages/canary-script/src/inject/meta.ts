/**
 * Meta/structured data injection.
 * Injects test payloads into meta tags, JSON-LD, and microdata elements
 * that AI agents may parse for page understanding.
 *
 * SECURITY: Uses textContent and setAttribute — never innerHTML — to prevent XSS.
 */

import type { DeliveryMethod } from '../types';

type MetaDeliveryMethod = Extract<DeliveryMethod, 'meta_tag' | 'json_ld' | 'microdata'>;

/** Set of delivery methods handled by the meta injector */
export const META_METHODS: Set<string> = new Set(['meta_tag', 'json_ld', 'microdata']);

/**
 * Create an element for meta/structured data delivery.
 * meta_tag and json_ld always go in <head>.
 * microdata can go anywhere in body.
 */
export function createMetaPayload(method: MetaDeliveryMethod, content: string, testId: string): Element {
  switch (method) {
    case 'meta_tag': {
      const meta = document.createElement('meta');
      meta.setAttribute('name', `canary-test-${testId}`);
      meta.setAttribute('content', content);
      return meta;
    }

    case 'json_ld': {
      const script = document.createElement('script');
      script.type = 'application/ld+json';
      script.setAttribute('data-canary-test', testId);

      // Build the JSON-LD object safely — no raw string concatenation
      const jsonLd = {
        '@context': 'https://schema.org',
        '@type': 'WebPageElement',
        'name': `canary-test-${testId}`,
        'description': content,
      };
      script.textContent = JSON.stringify(jsonLd);

      return script;
    }

    case 'microdata': {
      const el = document.createElement('div');
      el.setAttribute('itemscope', '');
      el.setAttribute('itemtype', 'https://schema.org/WebPageElement');
      el.style.display = 'none';
      el.setAttribute('data-canary-test', testId);

      const nameProp = document.createElement('meta');
      nameProp.setAttribute('itemprop', 'name');
      nameProp.setAttribute('content', `canary-test-${testId}`);
      el.appendChild(nameProp);

      const descProp = document.createElement('meta');
      descProp.setAttribute('itemprop', 'description');
      descProp.setAttribute('content', content);
      el.appendChild(descProp);

      return el;
    }

    default: {
      const el = document.createElement('div');
      el.style.display = 'none';
      el.setAttribute('data-canary-test', testId);
      el.textContent = content;
      return el;
    }
  }
}
