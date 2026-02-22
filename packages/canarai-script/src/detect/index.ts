/**
 * Detection orchestrator.
 * Combines user-agent matching, fingerprint analysis, and behavioral observation
 * into a single weighted detection result.
 */

import type { DetectionResult, DetectionSignals } from '../types';
import { matchUserAgent } from './useragent';
import { checkFingerprint } from './fingerprint';
import { observeBehavior } from './behavioral';

/** Scoring weights for each detection category */
const WEIGHTS = {
  userAgent: 0.40,
  fingerprint: 0.25,
  behavioral: 0.25,
  // network: 0.10 — reserved for server-side enrichment
} as const;

/** Classification thresholds */
const THRESHOLDS = {
  confirmed: 0.85,
  likely: 0.70,
  suspected: 0.50,
} as const;

/**
 * Classify a confidence score into a detection category.
 */
function classify(confidence: number): DetectionResult['classification'] {
  if (confidence >= THRESHOLDS.confirmed) return 'confirmed_agent';
  if (confidence >= THRESHOLDS.likely) return 'likely_agent';
  if (confidence >= THRESHOLDS.suspected) return 'suspected_agent';
  return 'human';
}

/**
 * Run the full detection pipeline.
 * Behavioral observation runs for ~2.5 seconds before the final score is computed.
 *
 * @param behaviorDurationMs - How long to observe behavior (default 2500ms)
 */
export async function runDetection(behaviorDurationMs: number = 2500): Promise<DetectionResult> {
  // Phase 1: Instant checks (synchronous)
  const uaResult = matchUserAgent();
  const fpResult = checkFingerprint();

  // Short-circuit: known crawler — return as human (not our concern)
  if (uaResult.isCrawler) {
    return {
      confidence: 0,
      classification: 'human',
      signals: {
        uaMatch: false,
        webdriver: false,
        headless: false,
        automationSignals: [],
        behavioralScore: 0,
        timingAnomalies: [],
      },
    };
  }

  // Short-circuit: known AI agent UA — confirmed with high confidence
  if (uaResult.matched) {
    // Still run fingerprint for signal richness, but skip behavioral wait
    const signals: DetectionSignals = {
      uaMatch: true,
      uaAgent: uaResult.agentFamily,
      webdriver: fpResult.webdriver,
      headless: fpResult.headless,
      automationSignals: fpResult.automationSignals,
      behavioralScore: 1.0, // Assumed bot
      timingAnomalies: [],
    };

    return {
      confidence: 1.0,
      classification: 'confirmed_agent',
      signals,
      agentFamily: uaResult.agentFamily,
    };
  }

  // Phase 2: Behavioral observation (async, waits for observation window)
  const behaviorResult = await observeBehavior(behaviorDurationMs);

  // Phase 3: Compute weighted score
  const uaScore = uaResult.matched ? 1.0 : 0.0;
  const fpScore = fpResult.score;
  const bhScore = behaviorResult.score;

  // Weighted average (network weight goes to 0 since we don't have server data)
  const adjustedWeightSum = WEIGHTS.userAgent + WEIGHTS.fingerprint + WEIGHTS.behavioral;
  const rawConfidence = (
    uaScore * WEIGHTS.userAgent +
    fpScore * WEIGHTS.fingerprint +
    bhScore * WEIGHTS.behavioral
  ) / adjustedWeightSum;

  // Clamp to [0, 1]
  const confidence = Math.max(0, Math.min(1, rawConfidence));

  const signals: DetectionSignals = {
    uaMatch: uaResult.matched,
    uaAgent: uaResult.agentFamily,
    webdriver: fpResult.webdriver,
    headless: fpResult.headless,
    automationSignals: fpResult.automationSignals,
    behavioralScore: bhScore,
    timingAnomalies: behaviorResult.timingAnomalies,
  };

  const classification = classify(confidence);

  return {
    confidence,
    classification,
    signals,
    agentFamily: uaResult.agentFamily,
  };
}
