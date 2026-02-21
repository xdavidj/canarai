import { describe, it, expect } from 'vitest';
import { injectAll } from '../../src/inject/index';
import { makeTestPayload } from '../helpers';
import type { DeliveryMethod, Placement } from '../../src/types';

describe('injectAll', () => {
  // ─── Routing to correct creator ──────────────────────────────────────────

  describe('routing to correct creator based on deliveryMethod', () => {
    it('routes css_display_none to DOM creator', () => {
      const payloads = [makeTestPayload({ deliveryMethod: 'css_display_none' })];
      const result = injectAll(payloads);
      expect(result.size).toBe(1);
      const el = result.get('test-001')!;
      expect(el.tagName).toBe('DIV');
      expect((el as HTMLElement).style.display).toBe('none');
    });

    it('routes meta_tag to META creator', () => {
      const payloads = [makeTestPayload({ deliveryMethod: 'meta_tag', testId: 'meta-test' })];
      const result = injectAll(payloads);
      expect(result.size).toBe(1);
      const el = result.get('meta-test')!;
      expect(el.tagName).toBe('META');
    });

    it('routes css_pseudo_element to STYLE creator', () => {
      const payloads = [makeTestPayload({ deliveryMethod: 'css_pseudo_element', testId: 'style-test' })];
      const result = injectAll(payloads);
      expect(result.size).toBe(1);
      const el = result.get('style-test')!;
      expect(el.tagName).toBe('DIV');
    });

    it('routes image_alt_text to STYLE creator', () => {
      const payloads = [makeTestPayload({ deliveryMethod: 'image_alt_text', testId: 'img-test' })];
      const result = injectAll(payloads);
      expect(result.size).toBe(1);
      const el = result.get('img-test')!;
      expect(el.tagName).toBe('IMG');
    });
  });

  // ─── Placement logic ────────────────────────────────────────────────────

  describe('placement logic', () => {
    it('body_top inserts as first child of body', () => {
      // Add a pre-existing element to body
      const existing = document.createElement('div');
      existing.id = 'existing';
      document.body.appendChild(existing);

      const payloads = [makeTestPayload({
        placement: 'body_top',
        testId: 'top-test',
      })];
      injectAll(payloads);

      expect(document.body.firstElementChild!.getAttribute('data-canarai-test')).toBe('top-test');
    });

    it('body_bottom appends as last child of body', () => {
      const existing = document.createElement('div');
      existing.id = 'existing';
      document.body.appendChild(existing);

      const payloads = [makeTestPayload({
        placement: 'body_bottom',
        testId: 'bottom-test',
      })];
      injectAll(payloads);

      expect(document.body.lastElementChild!.getAttribute('data-canarai-test')).toBe('bottom-test');
    });

    it('head placement inserts into head', () => {
      const payloads = [makeTestPayload({
        placement: 'head',
        testId: 'head-test',
      })];
      injectAll(payloads);

      const el = document.head.querySelector('[data-canarai-test="head-test"]');
      expect(el).not.toBeNull();
    });

    it('inline placement inserts into middle of body children', () => {
      // Create several children
      for (let i = 0; i < 6; i++) {
        const child = document.createElement('div');
        child.id = `child-${i}`;
        document.body.appendChild(child);
      }

      const payloads = [makeTestPayload({
        placement: 'inline',
        testId: 'inline-test',
      })];
      injectAll(payloads);

      // The element should be somewhere in the middle, not first or last
      const children = Array.from(document.body.children);
      const injectedIndex = children.findIndex(
        (el) => el.getAttribute('data-canarai-test') === 'inline-test'
      );
      expect(injectedIndex).toBeGreaterThan(0);
      expect(injectedIndex).toBeLessThan(children.length - 1);
    });
  });

  // ─── Forced placement for meta/json-ld ───────────────────────────────────

  describe('forced head placement', () => {
    it('meta_tag is forced to head regardless of payload.placement', () => {
      const payloads = [makeTestPayload({
        deliveryMethod: 'meta_tag',
        placement: 'body_bottom',
        testId: 'meta-forced',
      })];
      injectAll(payloads);

      // Should be in head, not body
      const inHead = document.head.querySelector('meta[name="canarai-test-meta-forced"]');
      expect(inHead).not.toBeNull();
    });

    it('json_ld is forced to head regardless of payload.placement', () => {
      const payloads = [makeTestPayload({
        deliveryMethod: 'json_ld',
        placement: 'body_bottom',
        testId: 'jsonld-forced',
      })];
      injectAll(payloads);

      // Should be in head, not body
      const inHead = document.head.querySelector('script[type="application/ld+json"]');
      expect(inHead).not.toBeNull();
    });
  });

  // ─── Error resilience ────────────────────────────────────────────────────

  describe('error resilience', () => {
    it('error in one injection does not break others', () => {
      const payloads = [
        makeTestPayload({ testId: 'good-1', deliveryMethod: 'css_display_none' }),
        // Use a delivery method that doesn't match any creator to see if it's handled
        makeTestPayload({ testId: 'unknown', deliveryMethod: 'html_comment' as DeliveryMethod }),
        makeTestPayload({ testId: 'good-2', deliveryMethod: 'css_visibility_hidden' }),
      ];

      const result = injectAll(payloads);
      // good-1 and good-2 should still be injected
      expect(result.has('good-1')).toBe(true);
      expect(result.has('good-2')).toBe(true);
    });
  });

  // ─── Return value ────────────────────────────────────────────────────────

  describe('return value', () => {
    it('returns a Map of testId -> Element', () => {
      const payloads = [
        makeTestPayload({ testId: 'map-test-1' }),
        makeTestPayload({ testId: 'map-test-2', deliveryMethod: 'aria_hidden' }),
      ];
      const result = injectAll(payloads);

      expect(result).toBeInstanceOf(Map);
      expect(result.size).toBe(2);
      expect(result.get('map-test-1')).toBeInstanceOf(Element);
      expect(result.get('map-test-2')).toBeInstanceOf(Element);
    });

    it('empty payloads array returns empty Map', () => {
      const result = injectAll([]);
      expect(result).toBeInstanceOf(Map);
      expect(result.size).toBe(0);
    });
  });
});
