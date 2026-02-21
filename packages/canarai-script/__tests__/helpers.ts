import type { TestPayload, DeliveryMethod, Placement, IngestPayload } from '../src/types';

export function makeTestPayload(overrides: Partial<TestPayload> = {}): TestPayload {
  return {
    testId: 'test-001',
    testVersion: '1.0.0',
    deliveryMethod: 'css_display_none' as DeliveryMethod,
    content: 'Test canary content with marker cnry_test12345678',
    placement: 'body_bottom' as Placement,
    canaraiMarkers: ['cnry_test12345678', 'cnry_test87654321'],
    ...overrides,
  };
}

export function makeIngestPayload(overrides: Partial<IngestPayload> = {}): IngestPayload {
  return {
    v: 1,
    site_key: 'ca_live_test123',
    visit_id: 'test-visit-001',
    timestamp: '2026-02-21T00:00:00Z',
    page_url: 'https://example.com/page',
    detection: {
      confidence: 0.9,
      signals: {
        uaMatch: true,
        webdriver: false,
        headless: false,
        automationSignals: [],
        behavioralScore: 0,
        timingAnomalies: [],
      },
      classification: 'confirmed_agent',
      agent_family: 'openai',
    },
    test_results: [],
    ...overrides,
  };
}

export function createScriptTag(attrs: Record<string, string> = {}): HTMLScriptElement {
  const script = document.createElement('script');
  for (const [key, value] of Object.entries(attrs)) {
    script.setAttribute(key, value);
  }
  document.head.appendChild(script);
  return script;
}
