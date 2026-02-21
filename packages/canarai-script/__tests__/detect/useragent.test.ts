import { describe, it, expect } from 'vitest';
import { matchUserAgent } from '../../src/detect/useragent';

describe('matchUserAgent', () => {
  // ─── AI Agent Pattern Matching ───────────────────────────────────────────

  describe('Anthropic agents', () => {
    it('matches ClaudeBot', () => {
      const result = matchUserAgent('Mozilla/5.0 ClaudeBot/1.0');
      expect(result.matched).toBe(true);
      expect(result.agentFamily).toBe('Anthropic Claude');
      expect(result.isCrawler).toBe(false);
    });

    it('matches Claude-Web', () => {
      const result = matchUserAgent('Claude-Web/1.0');
      expect(result.matched).toBe(true);
      expect(result.agentFamily).toBe('Anthropic Claude');
      expect(result.isCrawler).toBe(false);
    });

    it('matches anthropic-ai', () => {
      const result = matchUserAgent('anthropic-ai/1.0');
      expect(result.matched).toBe(true);
      expect(result.agentFamily).toBe('Anthropic Claude');
      expect(result.isCrawler).toBe(false);
    });

    it('matches Anthropic', () => {
      const result = matchUserAgent('Anthropic Agent');
      expect(result.matched).toBe(true);
      expect(result.agentFamily).toBe('Anthropic Claude');
      expect(result.isCrawler).toBe(false);
    });
  });

  describe('OpenAI agents', () => {
    it('matches ChatGPT-User', () => {
      const result = matchUserAgent('Mozilla/5.0 ChatGPT-User/1.0');
      expect(result.matched).toBe(true);
      expect(result.agentFamily).toBe('OpenAI ChatGPT');
      expect(result.isCrawler).toBe(false);
    });

    it('matches GPTBot', () => {
      const result = matchUserAgent('Mozilla/5.0 GPTBot/1.2');
      expect(result.matched).toBe(true);
      expect(result.agentFamily).toBe('OpenAI GPTBot');
      expect(result.isCrawler).toBe(false);
    });

    it('matches OAI-SearchBot', () => {
      const result = matchUserAgent('OAI-SearchBot/1.0');
      expect(result.matched).toBe(true);
      expect(result.agentFamily).toBe('OpenAI Search');
      expect(result.isCrawler).toBe(false);
    });

    it('matches OpenAI', () => {
      const result = matchUserAgent('OpenAI/2.0');
      expect(result.matched).toBe(true);
      expect(result.agentFamily).toBe('OpenAI');
      expect(result.isCrawler).toBe(false);
    });
  });

  describe('Google agents', () => {
    it('matches Google-Extended', () => {
      const result = matchUserAgent('Mozilla/5.0 Google-Extended');
      expect(result.matched).toBe(true);
      expect(result.agentFamily).toBe('Google Gemini');
      expect(result.isCrawler).toBe(false);
    });

    it('matches Gemini', () => {
      const result = matchUserAgent('Gemini/1.0');
      expect(result.matched).toBe(true);
      expect(result.agentFamily).toBe('Google Gemini');
      expect(result.isCrawler).toBe(false);
    });
  });

  describe('Other AI agents', () => {
    it('matches PerplexityBot', () => {
      const result = matchUserAgent('PerplexityBot/1.0');
      expect(result.matched).toBe(true);
      expect(result.agentFamily).toBe('Perplexity');
      expect(result.isCrawler).toBe(false);
    });

    it('matches cohere-ai', () => {
      const result = matchUserAgent('cohere-ai/1.0');
      expect(result.matched).toBe(true);
      expect(result.agentFamily).toBe('Cohere');
      expect(result.isCrawler).toBe(false);
    });

    it('matches CohereBot', () => {
      const result = matchUserAgent('CohereBot/1.0');
      expect(result.matched).toBe(true);
      expect(result.agentFamily).toBe('Cohere');
      expect(result.isCrawler).toBe(false);
    });

    it('matches AI2Bot', () => {
      const result = matchUserAgent('AI2Bot/1.0');
      expect(result.matched).toBe(true);
      expect(result.agentFamily).toBe('AI2');
      expect(result.isCrawler).toBe(false);
    });

    it('matches Meta-ExternalAgent', () => {
      const result = matchUserAgent('Meta-ExternalAgent/1.0');
      expect(result.matched).toBe(true);
      expect(result.agentFamily).toBe('Meta AI');
      expect(result.isCrawler).toBe(false);
    });

    it('matches FacebookBot', () => {
      const result = matchUserAgent('FacebookBot/1.0');
      expect(result.matched).toBe(true);
      expect(result.agentFamily).toBe('Meta');
      expect(result.isCrawler).toBe(false);
    });

    it('matches Applebot-Extended', () => {
      const result = matchUserAgent('Applebot-Extended/1.0');
      expect(result.matched).toBe(true);
      expect(result.agentFamily).toBe('Apple Intelligence');
      expect(result.isCrawler).toBe(false);
    });

    it('matches CCBot', () => {
      const result = matchUserAgent('CCBot/2.0');
      expect(result.matched).toBe(true);
      expect(result.agentFamily).toBe('Common Crawl');
      expect(result.isCrawler).toBe(false);
    });

    it('matches Diffbot', () => {
      const result = matchUserAgent('Diffbot/1.0');
      expect(result.matched).toBe(true);
      expect(result.agentFamily).toBe('Diffbot');
      expect(result.isCrawler).toBe(false);
    });

    it('matches Bytespider', () => {
      const result = matchUserAgent('Bytespider/1.0');
      expect(result.matched).toBe(true);
      expect(result.agentFamily).toBe('ByteDance');
      expect(result.isCrawler).toBe(false);
    });

    it('matches Amazonbot', () => {
      const result = matchUserAgent('Amazonbot/0.1');
      expect(result.matched).toBe(true);
      expect(result.agentFamily).toBe('Amazon');
      expect(result.isCrawler).toBe(false);
    });
  });

  describe('Browser automation agents', () => {
    it('matches HeadlessChrome', () => {
      const result = matchUserAgent('Mozilla/5.0 HeadlessChrome/120.0');
      expect(result.matched).toBe(true);
      expect(result.agentFamily).toBe('Headless Chrome');
      expect(result.isCrawler).toBe(false);
    });

    it('matches PhantomJS', () => {
      const result = matchUserAgent('Mozilla/5.0 PhantomJS/2.1');
      expect(result.matched).toBe(true);
      expect(result.agentFamily).toBe('PhantomJS');
      expect(result.isCrawler).toBe(false);
    });

    it('matches Selenium', () => {
      const result = matchUserAgent('Selenium/4.0');
      expect(result.matched).toBe(true);
      expect(result.agentFamily).toBe('Selenium');
      expect(result.isCrawler).toBe(false);
    });

    it('matches Puppeteer', () => {
      const result = matchUserAgent('Puppeteer/22.0');
      expect(result.matched).toBe(true);
      expect(result.agentFamily).toBe('Puppeteer');
      expect(result.isCrawler).toBe(false);
    });

    it('matches Playwright', () => {
      const result = matchUserAgent('Playwright/1.40');
      expect(result.matched).toBe(true);
      expect(result.agentFamily).toBe('Playwright');
      expect(result.isCrawler).toBe(false);
    });

    it('matches webdriver', () => {
      const result = matchUserAgent('Mozilla/5.0 webdriver');
      expect(result.matched).toBe(true);
      expect(result.agentFamily).toBe('WebDriver');
      expect(result.isCrawler).toBe(false);
    });
  });

  // ─── Known Crawler Exclusions ────────────────────────────────────────────

  describe('known crawler exclusions', () => {
    it('Googlebot is flagged as crawler, not matched as AI agent', () => {
      const result = matchUserAgent('Googlebot/2.1');
      expect(result.matched).toBe(false);
      expect(result.isCrawler).toBe(true);
    });

    it('Bingbot is flagged as crawler, not matched as AI agent', () => {
      const result = matchUserAgent('Mozilla/5.0 Bingbot/2.0');
      expect(result.matched).toBe(false);
      expect(result.isCrawler).toBe(true);
    });

    it('Slurp (Yahoo) is flagged as crawler', () => {
      const result = matchUserAgent('Mozilla/5.0 Slurp');
      expect(result.matched).toBe(false);
      expect(result.isCrawler).toBe(true);
    });

    it('DuckDuckBot is flagged as crawler', () => {
      const result = matchUserAgent('DuckDuckBot/1.0');
      expect(result.matched).toBe(false);
      expect(result.isCrawler).toBe(true);
    });

    it('AhrefsBot is flagged as crawler', () => {
      const result = matchUserAgent('AhrefsBot/7.0');
      expect(result.matched).toBe(false);
      expect(result.isCrawler).toBe(true);
    });
  });

  // ─── Case Insensitivity ──────────────────────────────────────────────────

  describe('case insensitivity', () => {
    it('"gptbot" (lowercase) should match', () => {
      const result = matchUserAgent('gptbot/1.0');
      expect(result.matched).toBe(true);
      expect(result.agentFamily).toBe('OpenAI GPTBot');
    });

    it('"CLAUDEBOT" (uppercase) should match', () => {
      const result = matchUserAgent('CLAUDEBOT/1.0');
      expect(result.matched).toBe(true);
      expect(result.agentFamily).toBe('Anthropic Claude');
    });

    it('"googlebot" (lowercase) should match as crawler', () => {
      const result = matchUserAgent('googlebot/2.1');
      expect(result.matched).toBe(false);
      expect(result.isCrawler).toBe(true);
    });
  });

  // ─── Edge Cases ──────────────────────────────────────────────────────────

  describe('edge cases', () => {
    it('empty string returns not matched, not crawler', () => {
      const result = matchUserAgent('');
      expect(result.matched).toBe(false);
      expect(result.isCrawler).toBe(false);
    });

    it('undefined returns not matched, not crawler', () => {
      const result = matchUserAgent(undefined);
      expect(result.matched).toBe(false);
      expect(result.isCrawler).toBe(false);
    });

    it('normal Chrome UA returns not matched, not crawler', () => {
      const result = matchUserAgent(
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
      );
      expect(result.matched).toBe(false);
      expect(result.isCrawler).toBe(false);
    });

    it('normal Firefox UA returns not matched, not crawler', () => {
      const result = matchUserAgent(
        'Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0'
      );
      expect(result.matched).toBe(false);
      expect(result.isCrawler).toBe(false);
    });

    it('UA containing both crawler and AI agent gives crawler precedence', () => {
      // Googlebot appears first in the string and in the check order
      const result = matchUserAgent('Googlebot/2.1 GPTBot/1.0');
      expect(result.matched).toBe(false);
      expect(result.isCrawler).toBe(true);
    });
  });
});
