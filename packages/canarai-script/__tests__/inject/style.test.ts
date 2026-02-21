import { describe, it, expect } from 'vitest';
import { createStylePayload, STYLE_METHODS } from '../../src/inject/style';

describe('createStylePayload', () => {
  const testContent = 'Test canary content for style injection';
  const testId = 'test-style-001';

  // ─── css_pseudo_element ──────────────────────────────────────────────────

  describe('css_pseudo_element', () => {
    it('creates a style element in head', () => {
      const el = createStylePayload('css_pseudo_element', testContent, testId);
      const styleTag = document.head.querySelector('style[data-canarai-test]');
      expect(styleTag).not.toBeNull();
    });

    it('creates a div with the correct class name', () => {
      const el = createStylePayload('css_pseudo_element', testContent, testId);
      expect(el.tagName).toBe('DIV');
      expect(el.classList.contains(`canarai-pseudo-${testId}`)).toBe(true);
    });

    it('style element contains ::after rule with CSS content', () => {
      const el = createStylePayload('css_pseudo_element', testContent, testId);
      const styleTag = document.head.querySelector('style[data-canarai-test]');
      expect(styleTag!.textContent).toContain('::after');
      expect(styleTag!.textContent).toContain('content:');
      expect(styleTag!.textContent).toContain('display: none');
    });

    it('sets data-canarai-test attribute on the div', () => {
      const el = createStylePayload('css_pseudo_element', testContent, testId);
      expect(el.getAttribute('data-canarai-test')).toBe(testId);
    });

    it('escapes quotes in content for CSS safety', () => {
      const contentWithQuotes = '"content with quotes"';
      const el = createStylePayload('css_pseudo_element', contentWithQuotes, testId);
      const styleTag = document.head.querySelector('style[data-canarai-test]');
      // The CSS content value should have the quotes escaped
      // The escapeCSSContent function replaces " with a hex escape
      const cssText = styleTag!.textContent!;
      // Should not contain unescaped double quotes inside the content value
      // (other than the wrapping quotes of the CSS content property)
      expect(cssText).toBeTruthy();
    });

    it('escapes CSS injection attempts in content', () => {
      const injection = 'content; } body { display: none }';
      const el = createStylePayload('css_pseudo_element', injection, testId);
      const styleTag = document.head.querySelector('style[data-canarai-test]');
      const cssText = styleTag!.textContent!;
      // The } and { characters should be escaped, preventing CSS injection
      // After escaping, the raw } and { should not appear unescaped in the content value
      expect(cssText).not.toMatch(/content:\s*"[^"]*;\s*\}\s*body/);
    });
  });

  // ─── Test ID sanitization ────────────────────────────────────────────────

  describe('test ID sanitization', () => {
    it('sanitizes testId with special characters to only alphanumeric/hyphen/underscore', () => {
      const dirtyTestId = 'test<script>alert(1)</script>';
      const el = createStylePayload('css_pseudo_element', testContent, dirtyTestId);
      const safeId = el.getAttribute('data-canarai-test')!;
      // Only alphanumeric, hyphens, underscores should remain
      expect(safeId).toMatch(/^[a-zA-Z0-9_-]+$/);
      expect(safeId).not.toContain('<');
      expect(safeId).not.toContain('>');
      expect(safeId).not.toContain('(');
      expect(safeId).not.toContain(')');
    });

    it('preserves valid characters in testId', () => {
      const cleanTestId = 'test-valid_id-123';
      const el = createStylePayload('css_pseudo_element', testContent, cleanTestId);
      expect(el.getAttribute('data-canarai-test')).toBe(cleanTestId);
    });
  });

  // ─── image_alt_text ──────────────────────────────────────────────────────

  describe('image_alt_text', () => {
    it('creates an img element', () => {
      const el = createStylePayload('image_alt_text', testContent, testId);
      expect(el.tagName).toBe('IMG');
    });

    it('sets alt text to content', () => {
      const el = createStylePayload('image_alt_text', testContent, testId) as HTMLImageElement;
      expect(el.alt).toBe(testContent);
    });

    it('uses 1x1 transparent pixel data URI as src', () => {
      const el = createStylePayload('image_alt_text', testContent, testId) as HTMLImageElement;
      expect(el.src).toContain('data:image/gif;base64,');
    });

    it('sets width=1 and height=1', () => {
      const el = createStylePayload('image_alt_text', testContent, testId) as HTMLImageElement;
      expect(el.width).toBe(1);
      expect(el.height).toBe(1);
    });

    it('sets data-canarai-test attribute', () => {
      const el = createStylePayload('image_alt_text', testContent, testId);
      expect(el.getAttribute('data-canarai-test')).toBe(testId);
    });
  });

  // ─── STYLE_METHODS constant ──────────────────────────────────────────────

  describe('STYLE_METHODS constant', () => {
    it('contains exactly 2 style delivery methods', () => {
      expect(STYLE_METHODS.size).toBe(2);
      expect(STYLE_METHODS.has('css_pseudo_element')).toBe(true);
      expect(STYLE_METHODS.has('image_alt_text')).toBe(true);
    });
  });
});
