import { describe, it, expect } from 'vitest';
import { getGuidance, getSeverity } from '../../src/remediate/guidance';
import type { DeliveryMethod } from '../../src/types';

describe('getSeverity', () => {
  it('returns critical for exfiltration_attempted', () => {
    expect(getSeverity('exfiltration_attempted')).toBe('critical');
  });

  it('returns high for full_compliance', () => {
    expect(getSeverity('full_compliance')).toBe('high');
  });

  it('returns medium for partial_compliance', () => {
    expect(getSeverity('partial_compliance')).toBe('medium');
  });

  it('returns medium for acknowledged', () => {
    expect(getSeverity('acknowledged')).toBe('medium');
  });

  it('returns medium for unknown outcomes', () => {
    expect(getSeverity('something_else')).toBe('medium');
  });
});

describe('getGuidance', () => {
  it('returns null for ignored outcomes (test passed)', () => {
    expect(getGuidance('css_display_none', 'ignored')).toBeNull();
  });

  it('returns guidance for css_display_none with exfiltration', () => {
    const guidance = getGuidance('css_display_none', 'exfiltration_attempted');
    expect(guidance).not.toBeNull();
    expect(guidance!.vulnerability).toBe('Instruction Override via CSS Hidden Text');
    expect(guidance!.severity).toBe('critical');
    expect(guidance!.steps.length).toBeGreaterThan(0);
    expect(guidance!.whatHappened).toContain('DATA LEAKED');
  });

  it('returns guidance for meta_tag with full_compliance', () => {
    const guidance = getGuidance('meta_tag', 'full_compliance');
    expect(guidance).not.toBeNull();
    expect(guidance!.severity).toBe('high');
    expect(guidance!.whatHappened).toContain('INSTRUCTIONS FOLLOWED');
  });

  it('returns guidance for data_attribute with acknowledged', () => {
    const guidance = getGuidance('data_attribute', 'acknowledged');
    expect(guidance).not.toBeNull();
    expect(guidance!.severity).toBe('medium');
    expect(guidance!.whatHappened).toContain('CONTENT NOTICED');
  });

  it('returns guidance for json_ld with partial_compliance', () => {
    const guidance = getGuidance('json_ld', 'partial_compliance');
    expect(guidance).not.toBeNull();
    expect(guidance!.severity).toBe('medium');
    expect(guidance!.whatHappened).toContain('PARTIALLY ENGAGED');
  });

  it('includes a reference URL for each delivery method', () => {
    const guidance = getGuidance('css_opacity_zero', 'exfiltration_attempted');
    expect(guidance!.reference).toBe('https://canar.ai/remediate/css_opacity_zero');
  });

  it('covers all 17 delivery methods', () => {
    const methods: DeliveryMethod[] = [
      'css_display_none', 'css_visibility_hidden', 'css_opacity_zero',
      'white_on_white_text', 'offscreen_positioning', 'zero_font_size',
      'html_comment', 'aria_hidden', 'meta_tag', 'json_ld', 'microdata',
      'image_alt_text', 'data_attribute', 'css_pseudo_element',
      'svg_text', 'noscript_block', 'form_hidden_field',
    ];

    for (const method of methods) {
      const guidance = getGuidance(method, 'exfiltration_attempted');
      expect(guidance, `Missing guidance for ${method}`).not.toBeNull();
      expect(guidance!.vulnerability).toBeTruthy();
      expect(guidance!.steps.length).toBeGreaterThan(0);
    }
  });
});
