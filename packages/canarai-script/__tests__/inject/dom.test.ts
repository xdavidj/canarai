import { describe, it, expect } from 'vitest';
import { createDOMPayload, DOM_METHODS } from '../../src/inject/dom';

describe('createDOMPayload', () => {
  const testContent = 'Test canary content with marker cnry_test12345678';
  const testId = 'test-001';

  // ─── css_display_none ────────────────────────────────────────────────────

  describe('css_display_none', () => {
    it('creates a div with display:none', () => {
      const el = createDOMPayload('css_display_none', testContent, testId);
      expect(el.tagName).toBe('DIV');
      expect((el as HTMLElement).style.display).toBe('none');
    });

    it('sets textContent to content', () => {
      const el = createDOMPayload('css_display_none', testContent, testId);
      expect(el.textContent).toBe(testContent);
    });

    it('sets data-canarai-test attribute to testId', () => {
      const el = createDOMPayload('css_display_none', testContent, testId);
      expect(el.getAttribute('data-canarai-test')).toBe(testId);
    });
  });

  // ─── css_visibility_hidden ───────────────────────────────────────────────

  describe('css_visibility_hidden', () => {
    it('creates a div with visibility:hidden', () => {
      const el = createDOMPayload('css_visibility_hidden', testContent, testId);
      expect(el.tagName).toBe('DIV');
      expect((el as HTMLElement).style.visibility).toBe('hidden');
    });

    it('sets textContent', () => {
      const el = createDOMPayload('css_visibility_hidden', testContent, testId);
      expect(el.textContent).toBe(testContent);
    });

    it('sets data-canarai-test attribute', () => {
      const el = createDOMPayload('css_visibility_hidden', testContent, testId);
      expect(el.getAttribute('data-canarai-test')).toBe(testId);
    });
  });

  // ─── css_opacity_zero ────────────────────────────────────────────────────

  describe('css_opacity_zero', () => {
    it('creates a div with opacity:0', () => {
      const el = createDOMPayload('css_opacity_zero', testContent, testId);
      expect(el.tagName).toBe('DIV');
      expect((el as HTMLElement).style.opacity).toBe('0');
    });

    it('sets textContent', () => {
      const el = createDOMPayload('css_opacity_zero', testContent, testId);
      expect(el.textContent).toBe(testContent);
    });

    it('sets data-canarai-test attribute', () => {
      const el = createDOMPayload('css_opacity_zero', testContent, testId);
      expect(el.getAttribute('data-canarai-test')).toBe(testId);
    });
  });

  // ─── white_on_white_text ─────────────────────────────────────────────────

  describe('white_on_white_text', () => {
    it('creates a div with white color and white background', () => {
      const el = createDOMPayload('white_on_white_text', testContent, testId) as HTMLElement;
      expect(el.tagName).toBe('DIV');
      // jsdom normalizes hex colors to rgb()
      expect(el.style.color).toBe('rgb(255, 255, 255)');
      expect(el.style.backgroundColor).toBe('rgb(255, 255, 255)');
    });

    it('sets textContent', () => {
      const el = createDOMPayload('white_on_white_text', testContent, testId);
      expect(el.textContent).toBe(testContent);
    });

    it('sets data-canarai-test attribute', () => {
      const el = createDOMPayload('white_on_white_text', testContent, testId);
      expect(el.getAttribute('data-canarai-test')).toBe(testId);
    });
  });

  // ─── offscreen_positioning ───────────────────────────────────────────────

  describe('offscreen_positioning', () => {
    it('creates a div with left:-9999px', () => {
      const el = createDOMPayload('offscreen_positioning', testContent, testId) as HTMLElement;
      expect(el.tagName).toBe('DIV');
      expect(el.style.left).toBe('-9999px');
    });

    it('sets textContent', () => {
      const el = createDOMPayload('offscreen_positioning', testContent, testId);
      expect(el.textContent).toBe(testContent);
    });

    it('sets data-canarai-test attribute', () => {
      const el = createDOMPayload('offscreen_positioning', testContent, testId);
      expect(el.getAttribute('data-canarai-test')).toBe(testId);
    });
  });

  // ─── zero_font_size ──────────────────────────────────────────────────────

  describe('zero_font_size', () => {
    it('creates a span with fontSize:0', () => {
      const el = createDOMPayload('zero_font_size', testContent, testId) as HTMLElement;
      expect(el.tagName).toBe('SPAN');
      // jsdom normalizes '0' to '0px'
      expect(el.style.fontSize).toBe('0px');
    });

    it('sets textContent', () => {
      const el = createDOMPayload('zero_font_size', testContent, testId);
      expect(el.textContent).toBe(testContent);
    });

    it('sets data-canarai-test attribute', () => {
      const el = createDOMPayload('zero_font_size', testContent, testId);
      expect(el.getAttribute('data-canarai-test')).toBe(testId);
    });
  });

  // ─── aria_hidden ─────────────────────────────────────────────────────────

  describe('aria_hidden', () => {
    it('creates a div with aria-hidden="true"', () => {
      const el = createDOMPayload('aria_hidden', testContent, testId);
      expect(el.tagName).toBe('DIV');
      expect(el.getAttribute('aria-hidden')).toBe('true');
    });

    it('sets textContent', () => {
      const el = createDOMPayload('aria_hidden', testContent, testId);
      expect(el.textContent).toBe(testContent);
    });

    it('sets data-canarai-test attribute', () => {
      const el = createDOMPayload('aria_hidden', testContent, testId);
      expect(el.getAttribute('data-canarai-test')).toBe(testId);
    });
  });

  // ─── form_hidden_field ───────────────────────────────────────────────────

  describe('form_hidden_field', () => {
    it('creates a form with a hidden input', () => {
      const el = createDOMPayload('form_hidden_field', testContent, testId);
      expect(el.tagName).toBe('FORM');
      const input = el.querySelector('input[type="hidden"]');
      expect(input).not.toBeNull();
    });

    it('hidden input has name = canarai_<testId>', () => {
      const el = createDOMPayload('form_hidden_field', testContent, testId);
      const input = el.querySelector('input[type="hidden"]') as HTMLInputElement;
      expect(input.name).toBe(`canarai_${testId}`);
    });

    it('hidden input value contains content', () => {
      const el = createDOMPayload('form_hidden_field', testContent, testId);
      const input = el.querySelector('input[type="hidden"]') as HTMLInputElement;
      expect(input.value).toBe(testContent);
    });

    it('sets data-canarai-test attribute on form', () => {
      const el = createDOMPayload('form_hidden_field', testContent, testId);
      expect(el.getAttribute('data-canarai-test')).toBe(testId);
    });
  });

  // ─── data_attribute ──────────────────────────────────────────────────────

  describe('data_attribute', () => {
    it('creates a div with data-canarai-instruction attribute', () => {
      const el = createDOMPayload('data_attribute', testContent, testId);
      expect(el.tagName).toBe('DIV');
      expect(el.getAttribute('data-canarai-instruction')).toBe(testContent);
    });

    it('sets data-canarai-test attribute', () => {
      const el = createDOMPayload('data_attribute', testContent, testId);
      expect(el.getAttribute('data-canarai-test')).toBe(testId);
    });
  });

  // ─── svg_text ────────────────────────────────────────────────────────────

  describe('svg_text', () => {
    it('creates an SVG element', () => {
      const el = createDOMPayload('svg_text', testContent, testId);
      expect(el.tagName.toLowerCase()).toBe('svg');
    });

    it('uses correct SVG namespace', () => {
      const el = createDOMPayload('svg_text', testContent, testId);
      expect(el.namespaceURI).toBe('http://www.w3.org/2000/svg');
    });

    it('contains a text element with content', () => {
      const el = createDOMPayload('svg_text', testContent, testId);
      const textEl = el.querySelector('text');
      expect(textEl).not.toBeNull();
      expect(textEl!.textContent).toBe(testContent);
    });

    it('text element also uses SVG namespace', () => {
      const el = createDOMPayload('svg_text', testContent, testId);
      const textEl = el.querySelector('text');
      expect(textEl!.namespaceURI).toBe('http://www.w3.org/2000/svg');
    });

    it('sets data-canarai-test attribute', () => {
      const el = createDOMPayload('svg_text', testContent, testId);
      expect(el.getAttribute('data-canarai-test')).toBe(testId);
    });
  });

  // ─── noscript_block ──────────────────────────────────────────────────────

  describe('noscript_block', () => {
    it('creates a noscript element', () => {
      const el = createDOMPayload('noscript_block', testContent, testId);
      expect(el.tagName).toBe('NOSCRIPT');
    });

    it('sets textContent', () => {
      const el = createDOMPayload('noscript_block', testContent, testId);
      expect(el.textContent).toBe(testContent);
    });

    it('sets data-canarai-test attribute', () => {
      const el = createDOMPayload('noscript_block', testContent, testId);
      expect(el.getAttribute('data-canarai-test')).toBe(testId);
    });
  });

  // ─── XSS Prevention (CRITICAL) ──────────────────────────────────────────

  describe('XSS prevention', () => {
    const xssContent = '<script>alert(1)</script>';

    it('css_display_none does not execute script in content', () => {
      const el = createDOMPayload('css_display_none', xssContent, testId);
      // textContent should contain the raw string, not parsed HTML
      expect(el.textContent).toBe(xssContent);
      // Should NOT have any child script elements
      expect(el.querySelector('script')).toBeNull();
    });

    it('css_visibility_hidden does not execute script in content', () => {
      const el = createDOMPayload('css_visibility_hidden', xssContent, testId);
      expect(el.textContent).toBe(xssContent);
      expect(el.querySelector('script')).toBeNull();
    });

    it('aria_hidden does not parse HTML from content', () => {
      const el = createDOMPayload('aria_hidden', xssContent, testId);
      expect(el.textContent).toBe(xssContent);
      expect(el.querySelector('script')).toBeNull();
    });

    it('data_attribute does not parse HTML from content', () => {
      const el = createDOMPayload('data_attribute', xssContent, testId);
      expect(el.getAttribute('data-canarai-instruction')).toBe(xssContent);
      expect(el.querySelector('script')).toBeNull();
    });

    it('svg_text does not parse HTML from content', () => {
      const el = createDOMPayload('svg_text', xssContent, testId);
      const textEl = el.querySelector('text');
      expect(textEl!.textContent).toBe(xssContent);
      expect(el.querySelector('script')).toBeNull();
    });

    it('form_hidden_field does not parse HTML from content', () => {
      const el = createDOMPayload('form_hidden_field', xssContent, testId);
      const input = el.querySelector('input[type="hidden"]') as HTMLInputElement;
      expect(input.value).toBe(xssContent);
      // No script element should exist
      expect(el.querySelector('script')).toBeNull();
    });
  });

  // ─── DOM_METHODS set ─────────────────────────────────────────────────────

  describe('DOM_METHODS constant', () => {
    it('contains all 11 DOM delivery methods', () => {
      expect(DOM_METHODS.size).toBe(11);
      expect(DOM_METHODS.has('css_display_none')).toBe(true);
      expect(DOM_METHODS.has('css_visibility_hidden')).toBe(true);
      expect(DOM_METHODS.has('css_opacity_zero')).toBe(true);
      expect(DOM_METHODS.has('white_on_white_text')).toBe(true);
      expect(DOM_METHODS.has('offscreen_positioning')).toBe(true);
      expect(DOM_METHODS.has('zero_font_size')).toBe(true);
      expect(DOM_METHODS.has('aria_hidden')).toBe(true);
      expect(DOM_METHODS.has('form_hidden_field')).toBe(true);
      expect(DOM_METHODS.has('data_attribute')).toBe(true);
      expect(DOM_METHODS.has('svg_text')).toBe(true);
      expect(DOM_METHODS.has('noscript_block')).toBe(true);
    });
  });
});
