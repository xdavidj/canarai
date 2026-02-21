import { describe, it, expect } from 'vitest';
import { isValidTestPayload, generateVisitId, generateCanaraiMarker } from '../src/index';
import { makeTestPayload } from './helpers';

describe('isValidTestPayload', () => {
  it('returns true for a valid payload', () => {
    const payload = makeTestPayload();
    expect(isValidTestPayload(payload)).toBe(true);
  });

  it('returns false for null', () => {
    expect(isValidTestPayload(null)).toBe(false);
  });

  it('returns false for non-object', () => {
    expect(isValidTestPayload('string')).toBe(false);
    expect(isValidTestPayload(42)).toBe(false);
  });

  it('returns false when testId is missing', () => {
    const payload = makeTestPayload();
    delete (payload as any).testId;
    expect(isValidTestPayload(payload)).toBe(false);
  });

  it('returns false when content is missing', () => {
    const payload = makeTestPayload();
    delete (payload as any).content;
    expect(isValidTestPayload(payload)).toBe(false);
  });

  it('returns false when deliveryMethod is missing', () => {
    const payload = makeTestPayload();
    delete (payload as any).deliveryMethod;
    expect(isValidTestPayload(payload)).toBe(false);
  });

  it('returns false when testVersion is missing', () => {
    const payload = makeTestPayload();
    delete (payload as any).testVersion;
    expect(isValidTestPayload(payload)).toBe(false);
  });

  it('returns false when placement is missing', () => {
    const payload = makeTestPayload();
    delete (payload as any).placement;
    expect(isValidTestPayload(payload)).toBe(false);
  });

  it('returns false when canaraiMarkers is missing', () => {
    const payload = makeTestPayload();
    delete (payload as any).canaraiMarkers;
    expect(isValidTestPayload(payload)).toBe(false);
  });

  it('returns false for unknown deliveryMethod', () => {
    const payload = makeTestPayload({ deliveryMethod: 'unknown_method' as any });
    expect(isValidTestPayload(payload)).toBe(false);
  });

  it('returns false when testId is too long (>64 chars)', () => {
    const payload = makeTestPayload({ testId: 'a'.repeat(65) });
    expect(isValidTestPayload(payload)).toBe(false);
  });

  it('returns false when testId has special characters', () => {
    const payload = makeTestPayload({ testId: 'test@#$%' });
    expect(isValidTestPayload(payload)).toBe(false);
  });

  it('returns false when testId has spaces', () => {
    const payload = makeTestPayload({ testId: 'test id with spaces' });
    expect(isValidTestPayload(payload)).toBe(false);
  });

  it('returns false when content is too long (>4096 chars)', () => {
    const payload = makeTestPayload({ content: 'x'.repeat(4097) });
    expect(isValidTestPayload(payload)).toBe(false);
  });

  it('returns false for invalid placement', () => {
    const payload = makeTestPayload({ placement: 'sidebar' as any });
    expect(isValidTestPayload(payload)).toBe(false);
  });

  it('accepts all valid delivery methods', () => {
    const methods = [
      'css_display_none', 'css_visibility_hidden', 'css_opacity_zero',
      'white_on_white_text', 'offscreen_positioning', 'zero_font_size',
      'html_comment', 'aria_hidden', 'meta_tag', 'json_ld', 'microdata',
      'image_alt_text', 'data_attribute', 'css_pseudo_element',
      'svg_text', 'noscript_block', 'form_hidden_field',
    ];

    for (const method of methods) {
      const payload = makeTestPayload({ deliveryMethod: method as any });
      expect(isValidTestPayload(payload)).toBe(true);
    }
  });

  it('accepts all valid placements', () => {
    const placements = ['body_top', 'body_bottom', 'inline', 'head'];
    for (const placement of placements) {
      const payload = makeTestPayload({ placement: placement as any });
      expect(isValidTestPayload(payload)).toBe(true);
    }
  });

  it('returns false when testId is empty string', () => {
    const payload = makeTestPayload({ testId: '' });
    expect(isValidTestPayload(payload)).toBe(false);
  });

  it('returns false when canaraiMarkers contains non-string values', () => {
    const payload = makeTestPayload();
    (payload as any).canaraiMarkers = [123, 'valid'];
    expect(isValidTestPayload(payload)).toBe(false);
  });
});

describe('generateVisitId', () => {
  it('returns UUID v4 format (8-4-4-4-12 hex)', () => {
    const id = generateVisitId();
    const uuidV4Regex = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
    expect(id).toMatch(uuidV4Regex);
  });

  it('version byte is 4', () => {
    const id = generateVisitId();
    // The 13th character (index 14 counting the hyphen) should be '4'
    const parts = id.split('-');
    expect(parts[2][0]).toBe('4');
  });

  it('variant byte is correct (8, 9, a, or b)', () => {
    const id = generateVisitId();
    const parts = id.split('-');
    expect(['8', '9', 'a', 'b']).toContain(parts[3][0]);
  });

  it('generates unique IDs', () => {
    const ids = new Set<string>();
    for (let i = 0; i < 100; i++) {
      ids.add(generateVisitId());
    }
    expect(ids.size).toBe(100);
  });

  it('returns a string of length 36', () => {
    const id = generateVisitId();
    expect(id.length).toBe(36);
  });
});

describe('generateCanaraiMarker', () => {
  it('starts with cnry_ prefix', () => {
    const marker = generateCanaraiMarker();
    expect(marker.startsWith('cnry_')).toBe(true);
  });

  it('length is 17 (5 prefix + 12 random)', () => {
    const marker = generateCanaraiMarker();
    expect(marker.length).toBe(17);
  });

  it('contains only lowercase alphanumeric characters after prefix', () => {
    const marker = generateCanaraiMarker();
    const suffix = marker.slice(5);
    expect(suffix).toMatch(/^[a-z0-9]+$/);
  });

  it('generates unique markers', () => {
    const markers = new Set<string>();
    for (let i = 0; i < 100; i++) {
      markers.add(generateCanaraiMarker());
    }
    expect(markers.size).toBe(100);
  });

  it('always starts with cnry_ across multiple calls', () => {
    for (let i = 0; i < 20; i++) {
      expect(generateCanaraiMarker().startsWith('cnry_')).toBe(true);
    }
  });
});
