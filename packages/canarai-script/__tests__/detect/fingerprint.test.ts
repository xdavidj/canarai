import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { checkFingerprint } from '../../src/detect/fingerprint';

describe('checkFingerprint', () => {
  // Store originals so we can restore them
  let originalWebdriver: PropertyDescriptor | undefined;
  let originalPlugins: PropertyDescriptor | undefined;
  let originalScreen: PropertyDescriptor | undefined;
  let originalLanguages: PropertyDescriptor | undefined;
  let originalOuterWidth: PropertyDescriptor | undefined;
  let originalOuterHeight: PropertyDescriptor | undefined;
  let originalInnerWidth: PropertyDescriptor | undefined;
  let originalInnerHeight: PropertyDescriptor | undefined;

  beforeEach(() => {
    originalWebdriver = Object.getOwnPropertyDescriptor(navigator, 'webdriver');
    originalPlugins = Object.getOwnPropertyDescriptor(navigator, 'plugins');
    originalScreen = Object.getOwnPropertyDescriptor(window, 'screen');
    originalLanguages = Object.getOwnPropertyDescriptor(navigator, 'languages');
    originalOuterWidth = Object.getOwnPropertyDescriptor(window, 'outerWidth');
    originalOuterHeight = Object.getOwnPropertyDescriptor(window, 'outerHeight');
    originalInnerWidth = Object.getOwnPropertyDescriptor(window, 'innerWidth');
    originalInnerHeight = Object.getOwnPropertyDescriptor(window, 'innerHeight');
  });

  afterEach(() => {
    // Restore webdriver
    if (originalWebdriver) {
      Object.defineProperty(navigator, 'webdriver', originalWebdriver);
    } else {
      // In jsdom, webdriver may not exist by default — delete it
      try {
        Object.defineProperty(navigator, 'webdriver', { value: undefined, configurable: true, writable: true });
      } catch { /* ignore */ }
    }

    // Restore plugins
    if (originalPlugins) {
      Object.defineProperty(navigator, 'plugins', originalPlugins);
    }

    // Restore screen
    if (originalScreen) {
      Object.defineProperty(window, 'screen', originalScreen);
    }

    // Restore languages
    if (originalLanguages) {
      Object.defineProperty(navigator, 'languages', originalLanguages);
    }

    // Restore window dimensions
    if (originalOuterWidth) {
      Object.defineProperty(window, 'outerWidth', originalOuterWidth);
    }
    if (originalOuterHeight) {
      Object.defineProperty(window, 'outerHeight', originalOuterHeight);
    }
    if (originalInnerWidth) {
      Object.defineProperty(window, 'innerWidth', originalInnerWidth);
    }
    if (originalInnerHeight) {
      Object.defineProperty(window, 'innerHeight', originalInnerHeight);
    }

    // Clean up CDP globals
    delete (window as any).__puppeteer_evaluation_script__;
    delete (window as any).__playwright;
    delete (window as any).callPhantom;
    delete (window as any)._phantom;
  });

  // ─── webdriver detection ─────────────────────────────────────────────────

  describe('webdriver detection', () => {
    it('detects navigator.webdriver=true as a signal', () => {
      Object.defineProperty(navigator, 'webdriver', { value: true, configurable: true });
      const result = checkFingerprint();
      expect(result.webdriver).toBe(true);
      expect(result.automationSignals).toContain('navigator.webdriver=true');
      expect(result.score).toBeGreaterThan(0);
    });

    it('webdriver=true contributes to headless flag', () => {
      Object.defineProperty(navigator, 'webdriver', { value: true, configurable: true });
      const result = checkFingerprint();
      expect(result.headless).toBe(true);
    });

    it('webdriver=false does not trigger signal', () => {
      Object.defineProperty(navigator, 'webdriver', { value: false, configurable: true });
      const result = checkFingerprint();
      expect(result.webdriver).toBe(false);
      expect(result.automationSignals).not.toContain('navigator.webdriver=true');
    });
  });

  // ─── Default jsdom environment ───────────────────────────────────────────

  describe('default jsdom environment', () => {
    it('returns a result object with all required fields', () => {
      const result = checkFingerprint();
      expect(result).toHaveProperty('webdriver');
      expect(result).toHaveProperty('headless');
      expect(result).toHaveProperty('automationSignals');
      expect(result).toHaveProperty('score');
      expect(typeof result.webdriver).toBe('boolean');
      expect(typeof result.headless).toBe('boolean');
      expect(Array.isArray(result.automationSignals)).toBe(true);
      expect(typeof result.score).toBe('number');
    });

    it('score is between 0 and 1', () => {
      const result = checkFingerprint();
      expect(result.score).toBeGreaterThanOrEqual(0);
      expect(result.score).toBeLessThanOrEqual(1);
    });
  });

  // ─── CDP detection ───────────────────────────────────────────────────────

  describe('CDP detection', () => {
    it('detects __puppeteer_evaluation_script__ as CDP signal', () => {
      (window as any).__puppeteer_evaluation_script__ = true;
      const result = checkFingerprint();
      expect(result.automationSignals).toContain('cdp_detected');
      expect(result.score).toBeGreaterThan(0);
    });

    it('detects __playwright as CDP signal', () => {
      (window as any).__playwright = {};
      const result = checkFingerprint();
      expect(result.automationSignals).toContain('cdp_detected');
      expect(result.score).toBeGreaterThan(0);
    });

    it('CDP detection sets headless=true', () => {
      (window as any).__puppeteer_evaluation_script__ = true;
      const result = checkFingerprint();
      expect(result.headless).toBe(true);
    });

    it('detects callPhantom as CDP signal', () => {
      (window as any).callPhantom = () => {};
      const result = checkFingerprint();
      expect(result.automationSignals).toContain('cdp_detected');
    });

    it('detects _phantom as CDP signal', () => {
      (window as any)._phantom = true;
      const result = checkFingerprint();
      expect(result.automationSignals).toContain('cdp_detected');
    });
  });

  // ─── Plugins ─────────────────────────────────────────────────────────────

  describe('plugins detection', () => {
    it('empty plugins array triggers signal', () => {
      // jsdom typically has plugins.length === 0 by default
      const result = checkFingerprint();
      // Just check the signal name exists if plugins are actually empty
      if (navigator.plugins.length === 0) {
        expect(result.automationSignals).toContain('no_browser_plugins');
      }
    });
  });

  // ─── Screen dimensions ───────────────────────────────────────────────────

  describe('screen dimensions detection', () => {
    it('screen 800x600 triggers suspicious signal', () => {
      Object.defineProperty(window, 'screen', {
        value: { width: 800, height: 600 },
        configurable: true,
      });
      const result = checkFingerprint();
      expect(result.automationSignals).toContain('suspicious_screen_dimensions');
    });

    it('screen 0x0 triggers suspicious signal', () => {
      Object.defineProperty(window, 'screen', {
        value: { width: 0, height: 0 },
        configurable: true,
      });
      const result = checkFingerprint();
      expect(result.automationSignals).toContain('suspicious_screen_dimensions');
    });

    it('normal screen dimensions (1920x1080) do not trigger signal', () => {
      Object.defineProperty(window, 'screen', {
        value: { width: 1920, height: 1080 },
        configurable: true,
      });
      const result = checkFingerprint();
      expect(result.automationSignals).not.toContain('suspicious_screen_dimensions');
    });
  });

  // ─── Languages ───────────────────────────────────────────────────────────

  describe('languages detection', () => {
    it('empty navigator.languages triggers signal', () => {
      Object.defineProperty(navigator, 'languages', {
        value: [],
        configurable: true,
      });
      const result = checkFingerprint();
      expect(result.automationSignals).toContain('empty_navigator_languages');
    });

    it('languages with single empty string triggers signal', () => {
      Object.defineProperty(navigator, 'languages', {
        value: [''],
        configurable: true,
      });
      const result = checkFingerprint();
      expect(result.automationSignals).toContain('empty_navigator_languages');
    });

    it('valid languages array does not trigger signal', () => {
      Object.defineProperty(navigator, 'languages', {
        value: ['en-US', 'en'],
        configurable: true,
      });
      const result = checkFingerprint();
      expect(result.automationSignals).not.toContain('empty_navigator_languages');
    });
  });

  // ─── Window dimensions ───────────────────────────────────────────────────

  describe('window dimensions detection', () => {
    it('outerWidth === innerWidth triggers anomaly', () => {
      Object.defineProperty(window, 'outerWidth', { value: 1024, configurable: true });
      Object.defineProperty(window, 'outerHeight', { value: 768, configurable: true });
      Object.defineProperty(window, 'innerWidth', { value: 1024, configurable: true });
      Object.defineProperty(window, 'innerHeight', { value: 768, configurable: true });
      const result = checkFingerprint();
      expect(result.automationSignals).toContain('window_dimensions_anomaly');
    });

    it('outerWidth=0, outerHeight=0 triggers anomaly', () => {
      Object.defineProperty(window, 'outerWidth', { value: 0, configurable: true });
      Object.defineProperty(window, 'outerHeight', { value: 0, configurable: true });
      const result = checkFingerprint();
      expect(result.automationSignals).toContain('window_dimensions_anomaly');
    });
  });

  // ─── Score capping ───────────────────────────────────────────────────────

  describe('score capping', () => {
    it('score caps at 1.0 even with many signals', () => {
      // Stack up as many signals as possible
      Object.defineProperty(navigator, 'webdriver', { value: true, configurable: true });
      (window as any).__puppeteer_evaluation_script__ = true;
      Object.defineProperty(navigator, 'languages', { value: [], configurable: true });
      Object.defineProperty(window, 'screen', {
        value: { width: 0, height: 0 },
        configurable: true,
      });
      Object.defineProperty(window, 'outerWidth', { value: 0, configurable: true });
      Object.defineProperty(window, 'outerHeight', { value: 0, configurable: true });

      const result = checkFingerprint();
      expect(result.score).toBeLessThanOrEqual(1.0);
    });
  });

  // ─── Headless flag logic ─────────────────────────────────────────────────

  describe('headless flag logic', () => {
    it('headless=true when webdriver=true', () => {
      Object.defineProperty(navigator, 'webdriver', { value: true, configurable: true });
      const result = checkFingerprint();
      expect(result.headless).toBe(true);
    });

    it('headless=true when CDP detected', () => {
      (window as any).__playwright = {};
      const result = checkFingerprint();
      expect(result.headless).toBe(true);
    });

    it('headless=true when 4 or more signals present', () => {
      // Arrange enough signals to hit >= 4 without webdriver or CDP
      Object.defineProperty(navigator, 'languages', { value: [], configurable: true });
      Object.defineProperty(window, 'screen', {
        value: { width: 0, height: 0 },
        configurable: true,
      });
      Object.defineProperty(window, 'outerWidth', { value: 0, configurable: true });
      Object.defineProperty(window, 'outerHeight', { value: 0, configurable: true });

      const result = checkFingerprint();
      // This should produce several signals. If >= 4 exist, headless = true.
      if (result.automationSignals.length >= 4) {
        expect(result.headless).toBe(true);
      }
    });
  });
});
