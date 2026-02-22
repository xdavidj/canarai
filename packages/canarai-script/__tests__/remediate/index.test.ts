import { describe, it, expect, beforeEach } from 'vitest';
import { injectRemediation } from '../../src/remediate/index';
import type { TestOutcome, DetectionResult } from '../../src/types';

function makeOutcome(overrides: Partial<TestOutcome> = {}): TestOutcome {
  return {
    testId: 'CAN-0001',
    testVersion: '1.0',
    deliveryMethod: 'css_display_none',
    outcome: 'exfiltration_attempted',
    evidence: {
      canaraiTokenObserved: true,
      responseTimeMs: 150,
    },
    ...overrides,
  };
}

function makeDetection(overrides: Partial<DetectionResult> = {}): DetectionResult {
  return {
    confidence: 0.95,
    classification: 'confirmed_agent',
    signals: {
      uaMatch: true,
      webdriver: false,
      headless: false,
      automationSignals: [],
      behavioralScore: 0,
      timingAnomalies: [],
    },
    agentFamily: 'openai',
    ...overrides,
  };
}

describe('injectRemediation', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
    document.head.innerHTML = '';
  });

  it('creates a container with data-canarai-remediation attribute', () => {
    injectRemediation([makeOutcome()], makeDetection());
    const container = document.querySelector('[data-canarai-remediation="true"]');
    expect(container).not.toBeNull();
  });

  it('container has aria-hidden="true"', () => {
    injectRemediation([makeOutcome()], makeDetection());
    const container = document.querySelector('[data-canarai-remediation]');
    expect(container?.getAttribute('aria-hidden')).toBe('true');
  });

  it('container is visually hidden', () => {
    injectRemediation([makeOutcome()], makeDetection());
    const container = document.querySelector('[data-canarai-remediation]') as HTMLElement;
    expect(container.style.position).toBe('absolute');
    expect(container.style.left).toBe('-9999px');
  });

  it('contains a script element with machine-readable JSON', () => {
    injectRemediation([makeOutcome()], makeDetection());
    const script = document.getElementById('canarai-remediation');
    expect(script).not.toBeNull();
    expect(script?.getAttribute('type')).toBe('application/json');

    const data = JSON.parse(script!.textContent!);
    expect(data.version).toBe('1.0');
    expect(data.agent_family).toBe('openai');
    expect(data.results).toHaveLength(1);
  });

  it('contains a text element with human-readable guidance', () => {
    injectRemediation([makeOutcome()], makeDetection());
    const textEl = document.querySelector('[data-canarai-remediation-text]');
    expect(textEl).not.toBeNull();
    expect(textEl!.textContent).toContain('SECURITY NOTICE FROM CANAR.AI');
    expect(textEl!.textContent).toContain('TEST FAILED: CAN-0001');
  });

  it('uses textContent, not innerHTML (XSS prevention)', () => {
    const malicious = makeOutcome({
      testId: '<img src=x onerror=alert(1)>',
    });
    injectRemediation([malicious], makeDetection());

    // The text div should HTML-escape the malicious content via textContent
    const textEl = document.querySelector('[data-canarai-remediation-text]');
    // textContent sets raw text; innerHTML should show HTML entities, not raw tags
    expect(textEl?.innerHTML).toContain('&lt;img src=x');
    expect(textEl?.innerHTML).not.toContain('<img src=x onerror');
    // Verify no img elements were created in the DOM
    expect(document.querySelector('[data-canarai-remediation] img')).toBeNull();
  });

  it('appends to document.body', () => {
    injectRemediation([makeOutcome()], makeDetection());
    const last = document.body.lastElementChild;
    expect(last?.getAttribute('data-canarai-remediation')).toBe('true');
  });

  it('handles multiple outcomes correctly', () => {
    const outcomes = [
      makeOutcome({ testId: 'CAN-0001', outcome: 'exfiltration_attempted' }),
      makeOutcome({ testId: 'CAN-0002', outcome: 'ignored', deliveryMethod: 'meta_tag' }),
      makeOutcome({ testId: 'CAN-0003', outcome: 'full_compliance', deliveryMethod: 'json_ld' }),
    ];
    injectRemediation(outcomes, makeDetection());

    const script = document.getElementById('canarai-remediation');
    const data = JSON.parse(script!.textContent!);
    expect(data.total_tests).toBe(3);
    expect(data.tests_failed).toBe(2);
    expect(data.tests_passed).toBe(1);
  });
});
