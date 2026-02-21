/**
 * DOM-based test payload injection.
 * Creates DOM elements using various hiding techniques to test whether
 * AI agents can discover and exfiltrate hidden content.
 *
 * SECURITY: Uses textContent and setAttribute — never innerHTML — to prevent XSS.
 */

import type { DeliveryMethod } from '../types';

type DOMDeliveryMethod = Extract<DeliveryMethod,
  | 'css_display_none' | 'css_visibility_hidden' | 'css_opacity_zero'
  | 'white_on_white_text' | 'offscreen_positioning' | 'zero_font_size'
  | 'aria_hidden' | 'form_hidden_field' | 'data_attribute'
  | 'svg_text' | 'noscript_block'
>;

/** Set of delivery methods handled by the DOM injector */
export const DOM_METHODS: Set<string> = new Set([
  'css_display_none', 'css_visibility_hidden', 'css_opacity_zero',
  'white_on_white_text', 'offscreen_positioning', 'zero_font_size',
  'aria_hidden', 'form_hidden_field', 'data_attribute',
  'svg_text', 'noscript_block',
]);

/**
 * Create a DOM element containing the test payload using the specified delivery method.
 * Returns the created element (caller is responsible for placement).
 */
export function createDOMPayload(method: DOMDeliveryMethod, content: string, testId: string): Element {
  switch (method) {
    case 'css_display_none': {
      const el = document.createElement('div');
      el.style.display = 'none';
      el.setAttribute('data-canarai-test', testId);
      el.textContent = content;
      return el;
    }

    case 'css_visibility_hidden': {
      const el = document.createElement('div');
      el.style.visibility = 'hidden';
      el.style.height = '0';
      el.style.overflow = 'hidden';
      el.setAttribute('data-canarai-test', testId);
      el.textContent = content;
      return el;
    }

    case 'css_opacity_zero': {
      const el = document.createElement('div');
      el.style.opacity = '0';
      el.style.position = 'absolute';
      el.style.pointerEvents = 'none';
      el.style.height = '0';
      el.style.overflow = 'hidden';
      el.setAttribute('data-canarai-test', testId);
      el.textContent = content;
      return el;
    }

    case 'white_on_white_text': {
      const el = document.createElement('div');
      el.style.color = '#ffffff';
      el.style.backgroundColor = '#ffffff';
      el.style.fontSize = '1px';
      el.style.lineHeight = '0';
      el.style.height = '0';
      el.style.overflow = 'hidden';
      el.setAttribute('data-canarai-test', testId);
      el.textContent = content;
      return el;
    }

    case 'offscreen_positioning': {
      const el = document.createElement('div');
      el.style.position = 'absolute';
      el.style.left = '-9999px';
      el.style.top = '-9999px';
      el.setAttribute('data-canarai-test', testId);
      el.textContent = content;
      return el;
    }

    case 'zero_font_size': {
      const el = document.createElement('span');
      el.style.fontSize = '0';
      el.style.lineHeight = '0';
      el.style.height = '0';
      el.style.width = '0';
      el.style.display = 'inline-block';
      el.style.overflow = 'hidden';
      el.setAttribute('data-canarai-test', testId);
      el.textContent = content;
      return el;
    }

    case 'aria_hidden': {
      const el = document.createElement('div');
      el.setAttribute('aria-hidden', 'true');
      el.style.position = 'absolute';
      el.style.height = '0';
      el.style.overflow = 'hidden';
      el.setAttribute('data-canarai-test', testId);
      el.textContent = content;
      return el;
    }

    case 'form_hidden_field': {
      const form = document.createElement('form');
      form.style.display = 'none';
      form.setAttribute('data-canarai-test', testId);
      form.setAttribute('aria-hidden', 'true');

      const input = document.createElement('input');
      input.type = 'hidden';
      input.name = `canarai_${testId}`;
      input.value = content;
      form.appendChild(input);

      return form;
    }

    case 'data_attribute': {
      const el = document.createElement('div');
      el.style.display = 'none';
      el.setAttribute('data-canarai-test', testId);
      el.setAttribute('data-canarai-instruction', content);
      return el;
    }

    case 'svg_text': {
      const svgNS = 'http://www.w3.org/2000/svg';
      const svg = document.createElementNS(svgNS, 'svg');
      svg.setAttribute('width', '0');
      svg.setAttribute('height', '0');
      svg.style.position = 'absolute';
      svg.style.overflow = 'hidden';
      svg.setAttribute('data-canarai-test', testId);

      const text = document.createElementNS(svgNS, 'text');
      text.textContent = content;
      svg.appendChild(text);

      return svg;
    }

    case 'noscript_block': {
      const el = document.createElement('noscript');
      el.setAttribute('data-canarai-test', testId);
      // noscript content won't be rendered in JS-enabled browsers.
      // We set textContent which is safe — it won't be parsed as HTML
      // since the noscript element's content model in a JS context is raw text.
      el.textContent = content;
      return el;
    }

    default: {
      // Fallback: hidden div
      const el = document.createElement('div');
      el.style.display = 'none';
      el.setAttribute('data-canarai-test', testId);
      el.textContent = content;
      return el;
    }
  }
}
