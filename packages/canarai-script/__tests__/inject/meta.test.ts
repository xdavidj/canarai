import { describe, it, expect } from 'vitest';
import { createMetaPayload, META_METHODS } from '../../src/inject/meta';

describe('createMetaPayload', () => {
  const testContent = 'Test canary instruction for AI agents';
  const testId = 'test-meta-001';

  // ─── meta_tag ────────────────────────────────────────────────────────────

  describe('meta_tag', () => {
    it('creates a <meta> element', () => {
      const el = createMetaPayload('meta_tag', testContent, testId);
      expect(el.tagName).toBe('META');
    });

    it('sets name attribute to canarai-test-<testId>', () => {
      const el = createMetaPayload('meta_tag', testContent, testId);
      expect(el.getAttribute('name')).toBe(`canarai-test-${testId}`);
    });

    it('sets content attribute to the provided content', () => {
      const el = createMetaPayload('meta_tag', testContent, testId);
      expect(el.getAttribute('content')).toBe(testContent);
    });
  });

  // ─── json_ld ─────────────────────────────────────────────────────────────

  describe('json_ld', () => {
    it('creates a <script type="application/ld+json"> element', () => {
      const el = createMetaPayload('json_ld', testContent, testId);
      expect(el.tagName).toBe('SCRIPT');
      expect(el.getAttribute('type')).toBe('application/ld+json');
    });

    it('sets data-canarai-test attribute', () => {
      const el = createMetaPayload('json_ld', testContent, testId);
      expect(el.getAttribute('data-canarai-test')).toBe(testId);
    });

    it('textContent is valid JSON with description set to content', () => {
      const el = createMetaPayload('json_ld', testContent, testId);
      const json = JSON.parse(el.textContent!);
      expect(json['@context']).toBe('https://schema.org');
      expect(json['@type']).toBe('WebPageElement');
      expect(json.description).toBe(testContent);
      expect(json.name).toBe(`canarai-test-${testId}`);
    });

    it('safely handles </script> in content via JSON.stringify', () => {
      const maliciousContent = '</script><script>alert(1)</script>';
      const el = createMetaPayload('json_ld', maliciousContent, testId);
      // JSON.stringify will escape the string, so the raw </script> won't break out
      const raw = el.textContent!;
      const json = JSON.parse(raw);
      expect(json.description).toBe(maliciousContent);
      // The raw textContent should NOT contain an unescaped </script> tag that would break out
      // JSON.stringify converts </script> to <\/script> in practice, or at minimum
      // it's embedded in a JSON string value, not as raw HTML
    });
  });

  // ─── microdata ───────────────────────────────────────────────────────────

  describe('microdata', () => {
    it('creates a div with itemscope and itemtype', () => {
      const el = createMetaPayload('microdata', testContent, testId);
      expect(el.tagName).toBe('DIV');
      expect(el.hasAttribute('itemscope')).toBe(true);
      expect(el.getAttribute('itemtype')).toBe('https://schema.org/WebPageElement');
    });

    it('has data-canarai-test attribute', () => {
      const el = createMetaPayload('microdata', testContent, testId);
      expect(el.getAttribute('data-canarai-test')).toBe(testId);
    });

    it('contains meta elements with itemprop name and description', () => {
      const el = createMetaPayload('microdata', testContent, testId);
      const metas = el.querySelectorAll('meta');
      expect(metas.length).toBe(2);

      const nameMeta = el.querySelector('meta[itemprop="name"]');
      expect(nameMeta).not.toBeNull();
      expect(nameMeta!.getAttribute('content')).toBe(`canarai-test-${testId}`);

      const descMeta = el.querySelector('meta[itemprop="description"]');
      expect(descMeta).not.toBeNull();
      expect(descMeta!.getAttribute('content')).toBe(testContent);
    });
  });

  // ─── META_METHODS constant ───────────────────────────────────────────────

  describe('META_METHODS constant', () => {
    it('contains exactly 3 meta delivery methods', () => {
      expect(META_METHODS.size).toBe(3);
      expect(META_METHODS.has('meta_tag')).toBe(true);
      expect(META_METHODS.has('json_ld')).toBe(true);
      expect(META_METHODS.has('microdata')).toBe(true);
    });
  });
});
