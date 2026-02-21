import type { CanaraiConfig } from './types';

declare global {
  interface Window {
    __CANARAI_CONFIG__?: Partial<CanaraiConfig>;
  }
}

const DEFAULTS: CanaraiConfig = {
  siteKey: '',
  endpoint: 'https://api.canar.ai/v1/ingest',
  enabledTests: [],
  detectionThreshold: 0.50,
  reportingMode: 'beacon',
  debug: false,
};

/**
 * Validate that an endpoint URL is on the allowlist.
 * Trusted sources: the script tag's data-canarai-endpoint (site-owner controlled),
 * canar.ai domains, and localhost/loopback for development.
 * Rejects endpoints injected via window.__CANARAI_CONFIG__ from untrusted scripts.
 */
function isAllowedEndpoint(url: string, scriptEndpoint?: string): boolean {
  try {
    const parsed = new URL(url);
    // Allow the endpoint set directly on the script tag (trusted by the site owner)
    if (scriptEndpoint && url === scriptEndpoint) return true;
    // Allow canar.ai domains
    if (parsed.hostname === 'canar.ai' || parsed.hostname.endsWith('.canar.ai')) return true;
    // Allow localhost/loopback for development
    if (parsed.hostname === 'localhost' || parsed.hostname === '127.0.0.1') return true;
    return false;
  } catch {
    return false;
  }
}

/**
 * Find the currently executing script tag for reading data-* attributes.
 * Falls back to searching for script[data-canarai-site-key].
 */
function findScriptTag(): HTMLScriptElement | null {
  // document.currentScript is set during synchronous script execution
  if (document.currentScript instanceof HTMLScriptElement) {
    return document.currentScript;
  }
  // Fallback: look for a script tag with canarai attributes
  return document.querySelector<HTMLScriptElement>('script[data-canarai-site-key]');
}

/**
 * Read config from data-* attributes on the script element.
 * Convention: data-canarai-site-key, data-canarai-endpoint, etc.
 */
function readScriptAttributes(): Partial<CanaraiConfig> {
  const script = findScriptTag();
  if (!script) return {};

  const config: Partial<CanaraiConfig> = {};

  const siteKey = script.getAttribute('data-canarai-site-key');
  if (siteKey) config.siteKey = siteKey;

  const endpoint = script.getAttribute('data-canarai-endpoint');
  if (endpoint) config.endpoint = endpoint;

  const enabledTests = script.getAttribute('data-canarai-tests');
  if (enabledTests) {
    config.enabledTests = enabledTests.split(',').map(t => t.trim()).filter(Boolean);
  }

  const threshold = script.getAttribute('data-canarai-threshold');
  if (threshold) {
    const parsed = parseFloat(threshold);
    if (!isNaN(parsed)) config.detectionThreshold = parsed;
  }

  const mode = script.getAttribute('data-canarai-reporting');
  if (mode === 'beacon' || mode === 'fetch' || mode === 'pixel') {
    config.reportingMode = mode;
  }

  const debug = script.getAttribute('data-canarai-debug');
  if (debug === 'true' || debug === '1') config.debug = true;

  return config;
}

/**
 * Resolve config by merging sources in priority order:
 * 1. data-* attributes on the script tag (site-owner controlled, trusted)
 * 2. window.__CANARAI_CONFIG__ (untrusted for endpoint — any script can set it)
 * 3. Defaults
 *
 * SECURITY: The endpoint field from __CANARAI_CONFIG__ is validated against an
 * allowlist. The script tag's data-canarai-endpoint is trusted because it is
 * placed by the site owner. If __CANARAI_CONFIG__ supplies an endpoint that
 * fails validation, we fall back to the script tag value or the default.
 */
export function resolveConfig(): CanaraiConfig {
  const windowConfig = window.__CANARAI_CONFIG__ || {};
  const scriptConfig = readScriptAttributes();

  // Script tag endpoint is the trusted reference (site owner controls the HTML)
  const scriptEndpoint = scriptConfig.endpoint;

  // Merge: defaults < scriptConfig < windowConfig for all fields except endpoint
  const merged: CanaraiConfig = {
    ...DEFAULTS,
    ...scriptConfig,
    ...windowConfig,
  };

  // For endpoint specifically: script tag takes priority over __CANARAI_CONFIG__,
  // then validate the final endpoint against the allowlist
  const trustedEndpoint = scriptEndpoint || DEFAULTS.endpoint;
  if (windowConfig.endpoint && windowConfig.endpoint !== trustedEndpoint) {
    // __CANARAI_CONFIG__ is trying to override the endpoint — validate it
    if (!isAllowedEndpoint(windowConfig.endpoint, scriptEndpoint)) {
      merged.endpoint = trustedEndpoint;
    }
  }

  return merged;
}
