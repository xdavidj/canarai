/**
 * CSS-based injection methods.
 * Injects test payloads via CSS pseudo-elements and image alt text.
 *
 * SECURITY: Uses textContent and setAttribute — never innerHTML — to prevent XSS.
 */

import type { DeliveryMethod } from '../types';

type StyleDeliveryMethod = Extract<DeliveryMethod, 'css_pseudo_element' | 'image_alt_text'>;

/** Set of delivery methods handled by the style injector */
export const STYLE_METHODS: Set<string> = new Set(['css_pseudo_element', 'image_alt_text']);

/**
 * Escape a string for safe use in a CSS content property value.
 * SECURITY: Escapes all non-alphanumeric/space/punctuation characters using
 * CSS hex escape sequences to prevent CSS injection via }, {, ;, quotes,
 * backslashes, and other special characters.
 */
function escapeCSSContent(str: string): string {
  return str.replace(/[^a-zA-Z0-9 .,!?:]/g, (char) => {
    return '\\' + char.charCodeAt(0).toString(16) + ' ';
  });
}

/**
 * Sanitize a testId for safe use in CSS class names.
 * Only allows alphanumeric characters, hyphens, and underscores.
 */
function sanitizeTestId(testId: string): string {
  return testId.replace(/[^a-zA-Z0-9_-]/g, '');
}

/**
 * Create element(s) for CSS-based delivery.
 * Returns the primary element to be inserted into the DOM.
 * For css_pseudo_element, also creates and appends a <style> tag to <head>.
 */
export function createStylePayload(method: StyleDeliveryMethod, content: string, testId: string): Element {
  // SECURITY: Sanitize testId before using in CSS class names or selectors
  const safeTestId = sanitizeTestId(testId);

  switch (method) {
    case 'css_pseudo_element': {
      // Generate a unique class name for this test
      const className = `canarai-pseudo-${safeTestId}`;

      // Create the style element with the ::after rule
      const style = document.createElement('style');
      style.setAttribute('data-canarai-test', `${safeTestId}-style`);
      style.textContent = `.${className}::after { content: "${escapeCSSContent(content)}"; display: none; }`;

      // Inject the style into head
      const head = document.head || document.getElementsByTagName('head')[0];
      if (head) {
        head.appendChild(style);
      }

      // Create the target element with the class
      const el = document.createElement('div');
      el.className = className;
      el.style.position = 'absolute';
      el.style.height = '0';
      el.style.overflow = 'hidden';
      el.setAttribute('data-canarai-test', safeTestId);

      return el;
    }

    case 'image_alt_text': {
      const img = document.createElement('img');
      // Use a 1x1 transparent pixel as src (data URI to avoid network request)
      img.src = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';
      img.alt = content;
      img.width = 1;
      img.height = 1;
      img.style.position = 'absolute';
      img.style.opacity = '0';
      img.style.pointerEvents = 'none';
      img.setAttribute('data-canarai-test', safeTestId);
      img.setAttribute('aria-hidden', 'true');

      return img;
    }

    default: {
      const el = document.createElement('div');
      el.style.display = 'none';
      el.setAttribute('data-canarai-test', safeTestId);
      el.textContent = content;
      return el;
    }
  }
}
