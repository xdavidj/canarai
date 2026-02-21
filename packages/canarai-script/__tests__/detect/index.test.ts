import { describe, it, expect, vi, beforeEach } from 'vitest';
import { runDetection } from '../../src/detect/index';
import * as useragentModule from '../../src/detect/useragent';
import * as fingerprintModule from '../../src/detect/fingerprint';
import * as behavioralModule from '../../src/detect/behavioral';

vi.mock('../../src/detect/useragent', () => ({
  matchUserAgent: vi.fn(),
}));

vi.mock('../../src/detect/fingerprint', () => ({
  checkFingerprint: vi.fn(),
}));

vi.mock('../../src/detect/behavioral', () => ({
  observeBehavior: vi.fn(),
}));

const mockMatchUA = vi.mocked(useragentModule.matchUserAgent);
const mockCheckFP = vi.mocked(fingerprintModule.checkFingerprint);
const mockObserveBehavior = vi.mocked(behavioralModule.observeBehavior);

describe('runDetection', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Default mocks: clean human-like environment
    mockMatchUA.mockReturnValue({
      matched: false,
      isCrawler: false,
    });

    mockCheckFP.mockReturnValue({
      webdriver: false,
      headless: false,
      automationSignals: [],
      score: 0,
    });

    mockObserveBehavior.mockResolvedValue({
      score: 0,
      timingAnomalies: [],
    });
  });

  // ─── Known crawler short-circuit ─────────────────────────────────────────

  describe('known crawler short-circuit', () => {
    it('returns human with confidence 0 for known crawlers', async () => {
      mockMatchUA.mockReturnValue({ matched: false, isCrawler: true });

      const result = await runDetection(100);
      expect(result.confidence).toBe(0);
      expect(result.classification).toBe('human');
      expect(result.signals.uaMatch).toBe(false);
    });

    it('does not call observeBehavior for known crawlers', async () => {
      mockMatchUA.mockReturnValue({ matched: false, isCrawler: true });

      await runDetection(100);
      expect(mockObserveBehavior).not.toHaveBeenCalled();
    });
  });

  // ─── Known AI agent short-circuit ────────────────────────────────────────

  describe('known AI agent short-circuit', () => {
    it('returns confirmed_agent with confidence 1.0 for matched AI UA', async () => {
      mockMatchUA.mockReturnValue({
        matched: true,
        agentFamily: 'Anthropic Claude',
        isCrawler: false,
      });

      const result = await runDetection(100);
      expect(result.confidence).toBe(1.0);
      expect(result.classification).toBe('confirmed_agent');
      expect(result.agentFamily).toBe('Anthropic Claude');
    });

    it('does not call observeBehavior for known AI agent', async () => {
      mockMatchUA.mockReturnValue({
        matched: true,
        agentFamily: 'OpenAI GPTBot',
        isCrawler: false,
      });

      await runDetection(100);
      expect(mockObserveBehavior).not.toHaveBeenCalled();
    });

    it('propagates agentFamily from UA match', async () => {
      mockMatchUA.mockReturnValue({
        matched: true,
        agentFamily: 'Google Gemini',
        isCrawler: false,
      });

      const result = await runDetection(100);
      expect(result.agentFamily).toBe('Google Gemini');
      expect(result.signals.uaAgent).toBe('Google Gemini');
    });

    it('includes fingerprint signals even for short-circuited AI agent', async () => {
      mockMatchUA.mockReturnValue({
        matched: true,
        agentFamily: 'Anthropic Claude',
        isCrawler: false,
      });
      mockCheckFP.mockReturnValue({
        webdriver: true,
        headless: true,
        automationSignals: ['navigator.webdriver=true'],
        score: 0.3,
      });

      const result = await runDetection(100);
      expect(result.signals.webdriver).toBe(true);
      expect(result.signals.headless).toBe(true);
      expect(result.signals.automationSignals).toContain('navigator.webdriver=true');
    });
  });

  // ─── Weighted scoring ────────────────────────────────────────────────────

  describe('weighted scoring computation', () => {
    it('no signals -> human classification', async () => {
      // All defaults -> score should be ~0
      const result = await runDetection(100);
      expect(result.classification).toBe('human');
      expect(result.confidence).toBeLessThan(0.50);
    });

    it('high fingerprint + high behavioral -> computed confidence', async () => {
      mockCheckFP.mockReturnValue({
        webdriver: true,
        headless: true,
        automationSignals: ['navigator.webdriver=true'],
        score: 0.9,
      });
      mockObserveBehavior.mockResolvedValue({
        score: 0.9,
        timingAnomalies: ['zero_interactions'],
      });

      const result = await runDetection(100);
      // UA score = 0 (not matched)
      // weighted = (0*0.40 + 0.9*0.25 + 0.9*0.25) / (0.40+0.25+0.25)
      // = (0 + 0.225 + 0.225) / 0.90 = 0.50
      expect(result.confidence).toBeCloseTo(0.50, 1);
      expect(result.classification).toBe('suspected_agent');
    });
  });

  // ─── Classification thresholds ───────────────────────────────────────────

  describe('classification thresholds', () => {
    it('>= 0.85 confidence -> confirmed_agent', async () => {
      // To get 0.85+, we need high scores across the board
      // Without UA match, max possible is (0*0.40 + 1.0*0.25 + 1.0*0.25) / 0.90 = 0.556
      // So we need UA match for confirmed_agent threshold
      // Test via direct mock: UA match short-circuits to 1.0 anyway
      // Let's verify the classify function indirectly
      mockMatchUA.mockReturnValue({
        matched: true,
        agentFamily: 'Test Agent',
        isCrawler: false,
      });
      const result = await runDetection(100);
      expect(result.confidence).toBeGreaterThanOrEqual(0.85);
      expect(result.classification).toBe('confirmed_agent');
    });

    it('>= 0.50 but < 0.70 -> suspected_agent', async () => {
      mockCheckFP.mockReturnValue({
        webdriver: true,
        headless: true,
        automationSignals: ['navigator.webdriver=true'],
        score: 0.9,
      });
      mockObserveBehavior.mockResolvedValue({
        score: 0.9,
        timingAnomalies: ['zero_interactions', 'no_mouse_movement'],
      });

      const result = await runDetection(100);
      // confidence ~ 0.50
      expect(result.confidence).toBeGreaterThanOrEqual(0.50);
      expect(result.confidence).toBeLessThan(0.70);
      expect(result.classification).toBe('suspected_agent');
    });

    it('< 0.50 -> human', async () => {
      mockCheckFP.mockReturnValue({
        webdriver: false,
        headless: false,
        automationSignals: [],
        score: 0.1,
      });
      mockObserveBehavior.mockResolvedValue({
        score: 0.1,
        timingAnomalies: [],
      });

      const result = await runDetection(100);
      // confidence ~ (0*0.40 + 0.1*0.25 + 0.1*0.25) / 0.90 = 0.056
      expect(result.confidence).toBeLessThan(0.50);
      expect(result.classification).toBe('human');
    });
  });

  // ─── Signal propagation ──────────────────────────────────────────────────

  describe('signal propagation', () => {
    it('propagates all fingerprint signals in result', async () => {
      mockCheckFP.mockReturnValue({
        webdriver: true,
        headless: true,
        automationSignals: ['navigator.webdriver=true', 'cdp_detected'],
        score: 0.6,
      });
      mockObserveBehavior.mockResolvedValue({
        score: 0.3,
        timingAnomalies: ['no_mouse_movement'],
      });

      const result = await runDetection(100);
      expect(result.signals.webdriver).toBe(true);
      expect(result.signals.headless).toBe(true);
      expect(result.signals.automationSignals).toEqual(['navigator.webdriver=true', 'cdp_detected']);
      expect(result.signals.timingAnomalies).toEqual(['no_mouse_movement']);
    });

    it('propagates behavioral score in result', async () => {
      mockObserveBehavior.mockResolvedValue({
        score: 0.7,
        timingAnomalies: ['zero_interactions'],
      });

      const result = await runDetection(100);
      expect(result.signals.behavioralScore).toBe(0.7);
    });

    it('result has all required DetectionResult fields', async () => {
      const result = await runDetection(100);
      expect(result).toHaveProperty('confidence');
      expect(result).toHaveProperty('classification');
      expect(result).toHaveProperty('signals');
      expect(result.signals).toHaveProperty('uaMatch');
      expect(result.signals).toHaveProperty('webdriver');
      expect(result.signals).toHaveProperty('headless');
      expect(result.signals).toHaveProperty('automationSignals');
      expect(result.signals).toHaveProperty('behavioralScore');
      expect(result.signals).toHaveProperty('timingAnomalies');
    });
  });

  // ─── Confidence clamping ─────────────────────────────────────────────────

  describe('confidence bounds', () => {
    it('confidence is always between 0 and 1', async () => {
      const result = await runDetection(100);
      expect(result.confidence).toBeGreaterThanOrEqual(0);
      expect(result.confidence).toBeLessThanOrEqual(1);
    });
  });
});
