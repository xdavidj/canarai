/**
 * Browser fingerprint-based automation detection.
 * Checks for signals that indicate headless browsers, automation frameworks,
 * or environments inconsistent with genuine user browsers.
 */

interface FingerprintResult {
  webdriver: boolean;
  headless: boolean;
  automationSignals: string[];
  score: number; // 0.0 (human) to 1.0 (automated)
}

/**
 * Check navigator.webdriver flag.
 * Set to true by WebDriver-compliant automation tools.
 */
function checkWebdriver(): boolean {
  try {
    return navigator.webdriver === true;
  } catch {
    return false;
  }
}

/**
 * Check for Chrome without proper chrome extension object.
 * Headless Chrome often has window.chrome but missing runtime.
 */
function checkChromeRuntime(): boolean {
  try {
    const w = window as unknown as Record<string, unknown>;
    if (w.chrome) {
      const chrome = w.chrome as Record<string, unknown>;
      // In real Chrome, chrome.runtime exists
      // In headless Chrome, it may be missing or empty
      if (!chrome.runtime || Object.keys(chrome.runtime as object).length === 0) {
        return true;
      }
    }
    return false;
  } catch {
    return false;
  }
}

/**
 * Check for missing or empty browser plugins.
 * Real browsers typically have at least a few plugins.
 */
function checkPlugins(): boolean {
  try {
    return navigator.plugins.length === 0;
  } catch {
    return false;
  }
}

/**
 * Check for suspicious screen dimensions.
 * Headless browsers often use default sizes like 800x600.
 */
function checkScreenDimensions(): boolean {
  try {
    const { width, height } = screen;
    // Zero dimensions = headless environment
    if (width === 0 || height === 0) return true;
    // Common headless default
    if (width === 800 && height === 600) return true;
    // Screen smaller than any real device
    if (width < 300 || height < 300) return true;
    return false;
  } catch {
    return false;
  }
}

/**
 * Check navigator.languages for anomalies.
 * Real browsers always have at least one language.
 */
function checkLanguages(): boolean {
  try {
    if (!navigator.languages || navigator.languages.length === 0) return true;
    // Single empty string
    if (navigator.languages.length === 1 && navigator.languages[0] === '') return true;
    return false;
  } catch {
    return false;
  }
}

/**
 * Check for missing Notification API.
 * Present in all modern browsers, often missing in headless.
 */
function checkNotificationAPI(): boolean {
  try {
    return typeof Notification === 'undefined';
  } catch {
    return false;
  }
}

/**
 * Check for Chrome DevTools Protocol presence.
 * CDP-controlled browsers expose certain properties.
 */
function checkCDP(): boolean {
  try {
    const w = window as unknown as Record<string, unknown>;
    // cdc_ prefix properties are injected by ChromeDriver
    for (const key in document) {
      if (key.startsWith('$cdc_') || key.startsWith('__cdc_')) return true;
    }
    // Puppeteer/Playwright may inject these
    if (w.__puppeteer_evaluation_script__ !== undefined) return true;
    if (w.__playwright !== undefined) return true;
    if (w.callPhantom !== undefined || w._phantom !== undefined) return true;
    return false;
  } catch {
    return false;
  }
}

/**
 * Check navigator.permissions for anomalies.
 * Some headless browsers have non-standard permissions behavior.
 */
function checkPermissions(): boolean {
  try {
    if (!navigator.permissions) return true;
    // In real browsers, permissions.query is a function
    if (typeof navigator.permissions.query !== 'function') return true;
    return false;
  } catch {
    return false;
  }
}

/**
 * Check for missing or broken connection API.
 */
function checkConnection(): boolean {
  try {
    const nav = navigator as unknown as Record<string, unknown>;
    // In real browsers on modern Chrome, connection exists
    // Its absence in Chrome UA is suspicious
    if (navigator.userAgent.includes('Chrome') && !nav.connection) return true;
    return false;
  } catch {
    return false;
  }
}

/**
 * Check window.outerWidth/outerHeight vs innerWidth/innerHeight.
 * In headless browsers, outer dimensions often equal inner dimensions (no chrome).
 */
function checkWindowDimensions(): boolean {
  try {
    if (window.outerWidth === 0 && window.outerHeight === 0) return true;
    // Outer exactly matching inner means no browser chrome — suspicious
    if (
      window.outerWidth === window.innerWidth &&
      window.outerHeight === window.innerHeight &&
      window.outerWidth > 0
    ) {
      return true;
    }
    return false;
  } catch {
    return false;
  }
}

/**
 * Run all fingerprint checks and produce a composite score.
 */
export function checkFingerprint(): FingerprintResult {
  const signals: string[] = [];
  let points = 0;
  const maxPoints = 10;

  const webdriver = checkWebdriver();
  if (webdriver) {
    signals.push('navigator.webdriver=true');
    points += 3; // Strong signal
  }

  if (checkChromeRuntime()) {
    signals.push('chrome_runtime_missing');
    points += 1;
  }

  const noPlugins = checkPlugins();
  if (noPlugins) {
    signals.push('no_browser_plugins');
    points += 1;
  }

  if (checkScreenDimensions()) {
    signals.push('suspicious_screen_dimensions');
    points += 1;
  }

  if (checkLanguages()) {
    signals.push('empty_navigator_languages');
    points += 1;
  }

  if (checkNotificationAPI()) {
    signals.push('notification_api_missing');
    points += 1;
  }

  const cdp = checkCDP();
  if (cdp) {
    signals.push('cdp_detected');
    points += 3; // Strong signal
  }

  if (checkPermissions()) {
    signals.push('permissions_api_anomaly');
    points += 1;
  }

  if (checkConnection()) {
    signals.push('connection_api_missing_in_chrome');
    points += 1;
  }

  if (checkWindowDimensions()) {
    signals.push('window_dimensions_anomaly');
    points += 1;
  }

  const headless = webdriver || cdp || signals.length >= 4;
  const score = Math.min(points / maxPoints, 1.0);

  return {
    webdriver,
    headless,
    automationSignals: signals,
    score,
  };
}
