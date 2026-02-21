export interface CanaryConfig {
  siteKey: string;
  endpoint: string;
  enabledTests?: string[];
  detectionThreshold?: number;
  reportingMode?: 'beacon' | 'fetch' | 'pixel';
  debug?: boolean;
}

export interface DetectionResult {
  confidence: number;
  classification: 'confirmed_agent' | 'likely_agent' | 'suspected_agent' | 'human';
  signals: DetectionSignals;
  agentFamily?: string;
}

export interface DetectionSignals {
  uaMatch: boolean;
  uaAgent?: string;
  webdriver: boolean;
  headless: boolean;
  automationSignals: string[];
  behavioralScore: number;
  timingAnomalies: string[];
}

export type DeliveryMethod =
  | 'css_display_none' | 'css_visibility_hidden' | 'css_opacity_zero'
  | 'white_on_white_text' | 'offscreen_positioning' | 'zero_font_size'
  | 'html_comment' | 'aria_hidden' | 'meta_tag' | 'json_ld' | 'microdata'
  | 'image_alt_text' | 'data_attribute' | 'css_pseudo_element'
  | 'svg_text' | 'noscript_block' | 'form_hidden_field';

export type Placement = 'body_top' | 'body_bottom' | 'inline' | 'head';

export interface TestPayload {
  testId: string;
  testVersion: string;
  deliveryMethod: DeliveryMethod;
  content: string;
  placement: Placement;
  canaryMarkers: string[];
}

export interface TestOutcome {
  testId: string;
  testVersion: string;
  deliveryMethod: DeliveryMethod;
  outcome: 'exfiltration_attempted' | 'full_compliance' | 'partial_compliance' | 'acknowledged' | 'ignored';
  evidence: {
    canaryTokenObserved: boolean;
    responseTimeMs: number;
    domMutations?: string[];
    networkRequests?: string[];
  };
}

export interface IngestPayload {
  v: 1;
  site_key: string;
  visit_id: string;
  timestamp: string;
  page_url: string;
  detection: {
    confidence: number;
    signals: DetectionSignals;
    classification: string;
    agent_family?: string;
  };
  test_results: Array<{
    test_id: string;
    test_version: string;
    delivery_method: string;
    outcome: string;
    evidence: Record<string, unknown>;
  }>;
}
