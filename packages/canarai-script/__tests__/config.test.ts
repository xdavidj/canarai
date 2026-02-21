import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { resolveConfig } from '../src/config';
import { createScriptTag } from './helpers';

describe('resolveConfig', () => {
  afterEach(() => {
    // Clean up script tags and window config
    document.head.innerHTML = '';
    document.body.innerHTML = '';
    delete (window as any).__CANARAI_CONFIG__;
  });

  it('returns default config values when no overrides', () => {
    const config = resolveConfig();
    expect(config.siteKey).toBe('');
    expect(config.endpoint).toBe('https://api.canar.ai/v1/ingest');
    expect(config.enabledTests).toEqual([]);
    expect(config.detectionThreshold).toBe(0.50);
    expect(config.reportingMode).toBe('beacon');
    expect(config.debug).toBe(false);
  });

  it('data-* attributes on script tag override defaults', () => {
    createScriptTag({
      'data-canarai-site-key': 'ca_live_mysite',
      'data-canarai-endpoint': 'https://custom.canar.ai/v1/ingest',
      'data-canarai-reporting': 'fetch',
    });

    const config = resolveConfig();
    expect(config.siteKey).toBe('ca_live_mysite');
    expect(config.endpoint).toBe('https://custom.canar.ai/v1/ingest');
    expect(config.reportingMode).toBe('fetch');
  });

  it('window.__CANARAI_CONFIG__ overrides defaults', () => {
    window.__CANARAI_CONFIG__ = {
      siteKey: 'ca_live_window',
      debug: true,
    };

    const config = resolveConfig();
    expect(config.siteKey).toBe('ca_live_window');
    expect(config.debug).toBe(true);
  });

  it('window.__CANARAI_CONFIG__ overrides script tag for non-endpoint fields', () => {
    createScriptTag({
      'data-canarai-site-key': 'ca_live_script',
    });

    window.__CANARAI_CONFIG__ = {
      siteKey: 'ca_live_window_override',
    };

    const config = resolveConfig();
    // Window config takes priority in the merge (spread order)
    expect(config.siteKey).toBe('ca_live_window_override');
  });

  it('*.canar.ai endpoint is allowed', () => {
    window.__CANARAI_CONFIG__ = {
      endpoint: 'https://custom.canar.ai/v1/ingest',
    };

    const config = resolveConfig();
    expect(config.endpoint).toBe('https://custom.canar.ai/v1/ingest');
  });

  it('localhost endpoint is allowed', () => {
    window.__CANARAI_CONFIG__ = {
      endpoint: 'http://localhost:8787/v1/ingest',
    };

    const config = resolveConfig();
    expect(config.endpoint).toBe('http://localhost:8787/v1/ingest');
  });

  it('untrusted endpoint from __CANARAI_CONFIG__ is rejected, falls back to default', () => {
    window.__CANARAI_CONFIG__ = {
      endpoint: 'https://evil.com/steal',
    };

    const config = resolveConfig();
    expect(config.endpoint).toBe('https://api.canar.ai/v1/ingest');
  });

  it('script tag endpoint is always trusted (site-owner controlled)', () => {
    createScriptTag({
      'data-canarai-site-key': 'ca_live_test',
      'data-canarai-endpoint': 'https://my-custom-server.com/v1/ingest',
    });

    const config = resolveConfig();
    expect(config.endpoint).toBe('https://my-custom-server.com/v1/ingest');
  });

  it('untrusted __CANARAI_CONFIG__ endpoint falls back to script tag endpoint', () => {
    createScriptTag({
      'data-canarai-site-key': 'ca_live_test',
      'data-canarai-endpoint': 'https://api.canar.ai/v1/ingest',
    });

    window.__CANARAI_CONFIG__ = {
      endpoint: 'https://evil.com/steal',
    };

    const config = resolveConfig();
    expect(config.endpoint).toBe('https://api.canar.ai/v1/ingest');
  });

  it('data-canarai-threshold parsed as float', () => {
    createScriptTag({
      'data-canarai-site-key': 'ca_live_test',
      'data-canarai-threshold': '0.85',
    });

    const config = resolveConfig();
    expect(config.detectionThreshold).toBe(0.85);
  });

  it('data-canarai-debug="true" sets debug: true', () => {
    createScriptTag({
      'data-canarai-site-key': 'ca_live_test',
      'data-canarai-debug': 'true',
    });

    const config = resolveConfig();
    expect(config.debug).toBe(true);
  });

  it('data-canarai-debug="1" sets debug: true', () => {
    createScriptTag({
      'data-canarai-site-key': 'ca_live_test',
      'data-canarai-debug': '1',
    });

    const config = resolveConfig();
    expect(config.debug).toBe(true);
  });

  it('data-canarai-tests="a,b,c" parsed to array', () => {
    createScriptTag({
      'data-canarai-site-key': 'ca_live_test',
      'data-canarai-tests': 'css_display_none,meta_tag,json_ld',
    });

    const config = resolveConfig();
    expect(config.enabledTests).toEqual(['css_display_none', 'meta_tag', 'json_ld']);
  });

  it('data-canarai-reporting accepts beacon', () => {
    createScriptTag({
      'data-canarai-site-key': 'ca_live_test',
      'data-canarai-reporting': 'beacon',
    });

    const config = resolveConfig();
    expect(config.reportingMode).toBe('beacon');
  });

  it('data-canarai-reporting accepts fetch', () => {
    createScriptTag({
      'data-canarai-site-key': 'ca_live_test',
      'data-canarai-reporting': 'fetch',
    });

    const config = resolveConfig();
    expect(config.reportingMode).toBe('fetch');
  });

  it('data-canarai-reporting accepts pixel', () => {
    createScriptTag({
      'data-canarai-site-key': 'ca_live_test',
      'data-canarai-reporting': 'pixel',
    });

    const config = resolveConfig();
    expect(config.reportingMode).toBe('pixel');
  });

  it('data-canarai-reporting ignores invalid values', () => {
    createScriptTag({
      'data-canarai-site-key': 'ca_live_test',
      'data-canarai-reporting': 'websocket',
    });

    const config = resolveConfig();
    // Should remain the default
    expect(config.reportingMode).toBe('beacon');
  });
});
