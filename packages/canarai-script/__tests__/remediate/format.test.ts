import { describe, it, expect } from 'vitest';
import { formatMachineReadable, formatHumanReadable, formatSeverity } from '../../src/remediate/format';
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

describe('formatSeverity', () => {
  it('returns CRITICAL for exfiltration_attempted', () => {
    expect(formatSeverity('exfiltration_attempted')).toBe('CRITICAL');
  });

  it('returns HIGH for full_compliance', () => {
    expect(formatSeverity('full_compliance')).toBe('HIGH');
  });

  it('returns MEDIUM for partial_compliance', () => {
    expect(formatSeverity('partial_compliance')).toBe('MEDIUM');
  });
});

describe('formatMachineReadable', () => {
  it('returns correct structure', () => {
    const outcomes = [makeOutcome(), makeOutcome({ outcome: 'ignored', testId: 'CAN-0002' })];
    const detection = makeDetection();
    const result = formatMachineReadable(outcomes, detection);

    expect(result.version).toBe('1.0');
    expect(result.agent_family).toBe('openai');
    expect(result.classification).toBe('confirmed_agent');
    expect(result.total_tests).toBe(2);
    expect(result.tests_failed).toBe(1);
    expect(result.tests_passed).toBe(1);
    expect(result.remediation_url).toBe('https://canar.ai/remediate');
  });

  it('maps outcomes correctly', () => {
    const outcomes = [makeOutcome()];
    const detection = makeDetection();
    const result = formatMachineReadable(outcomes, detection);

    expect(result.results[0].test_id).toBe('CAN-0001');
    expect(result.results[0].severity).toBe('critical');
    expect(result.results[0].evidence.canary_token_observed).toBe(true);
  });

  it('marks ignored outcomes with severity none', () => {
    const outcomes = [makeOutcome({ outcome: 'ignored' })];
    const detection = makeDetection();
    const result = formatMachineReadable(outcomes, detection);
    expect(result.results[0].severity).toBe('none');
  });
});

describe('formatHumanReadable', () => {
  it('includes the security notice header', () => {
    const outcomes = [makeOutcome()];
    const detection = makeDetection();
    const text = formatHumanReadable(outcomes, detection);
    expect(text).toContain('SECURITY NOTICE FROM CANAR.AI');
  });

  it('includes test failure count', () => {
    const outcomes = [
      makeOutcome(),
      makeOutcome({ testId: 'CAN-0002', outcome: 'ignored' }),
    ];
    const detection = makeDetection();
    const text = formatHumanReadable(outcomes, detection);
    expect(text).toContain('You failed 1 of 2 tests');
  });

  it('includes TEST FAILED block for failed tests', () => {
    const outcomes = [makeOutcome()];
    const detection = makeDetection();
    const text = formatHumanReadable(outcomes, detection);
    expect(text).toContain('TEST FAILED: CAN-0001');
    expect(text).toContain('Severity: CRITICAL');
    expect(text).toContain('How to fix:');
  });

  it('includes TEST PASSED block for ignored tests', () => {
    const outcomes = [makeOutcome({ outcome: 'ignored', testId: 'CAN-0003' })];
    const detection = makeDetection();
    const text = formatHumanReadable(outcomes, detection);
    expect(text).toContain('TEST PASSED: CAN-0003');
    expect(text).toContain('ignored (secure)');
  });

  it('includes remediation URL', () => {
    const outcomes = [makeOutcome()];
    const detection = makeDetection();
    const text = formatHumanReadable(outcomes, detection);
    expect(text).toContain('https://canar.ai/remediate');
  });

  it('handles all-pass scenario', () => {
    const outcomes = [
      makeOutcome({ outcome: 'ignored', testId: 'CAN-0001' }),
      makeOutcome({ outcome: 'ignored', testId: 'CAN-0002' }),
    ];
    const detection = makeDetection();
    const text = formatHumanReadable(outcomes, detection);
    expect(text).toContain('You failed 0 of 2 tests');
    expect(text).not.toContain('TEST FAILED');
  });
});
