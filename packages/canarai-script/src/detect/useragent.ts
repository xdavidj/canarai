/**
 * User-Agent based AI agent detection.
 * Matches known AI agent UA strings and returns the agent family.
 */

interface UAMatchResult {
  matched: boolean;
  agentFamily?: string;
  isCrawler: boolean;
}

/**
 * Known AI agent UA patterns with their family names.
 * Order matters — more specific patterns first.
 */
const AI_AGENT_PATTERNS: Array<{ pattern: RegExp; family: string }> = [
  // Anthropic
  { pattern: /ClaudeBot/i, family: 'Anthropic Claude' },
  { pattern: /Claude-Web/i, family: 'Anthropic Claude' },
  { pattern: /anthropic-ai/i, family: 'Anthropic Claude' },
  { pattern: /Anthropic/i, family: 'Anthropic Claude' },

  // OpenAI
  { pattern: /ChatGPT-User/i, family: 'OpenAI ChatGPT' },
  { pattern: /GPTBot/i, family: 'OpenAI GPTBot' },
  { pattern: /OAI-SearchBot/i, family: 'OpenAI Search' },
  { pattern: /OpenAI/i, family: 'OpenAI' },

  // Google
  { pattern: /Google-Extended/i, family: 'Google Gemini' },
  { pattern: /Gemini/i, family: 'Google Gemini' },

  // Perplexity
  { pattern: /PerplexityBot/i, family: 'Perplexity' },

  // Cohere
  { pattern: /cohere-ai/i, family: 'Cohere' },
  { pattern: /CohereBot/i, family: 'Cohere' },

  // AI2
  { pattern: /AI2Bot/i, family: 'AI2' },
  { pattern: /Ai2Bot-Dolma/i, family: 'AI2 Dolma' },

  // Meta
  { pattern: /Meta-ExternalAgent/i, family: 'Meta AI' },
  { pattern: /FacebookBot/i, family: 'Meta' },
  { pattern: /meta-externalfetcher/i, family: 'Meta AI' },

  // Apple
  { pattern: /Applebot-Extended/i, family: 'Apple Intelligence' },

  // Common Crawl / Dataset builders
  { pattern: /CCBot/i, family: 'Common Crawl' },
  { pattern: /Diffbot/i, family: 'Diffbot' },

  // ByteDance
  { pattern: /Bytespider/i, family: 'ByteDance' },

  // Amazon
  { pattern: /Amazonbot/i, family: 'Amazon' },

  // Browser automation / headless
  { pattern: /HeadlessChrome/i, family: 'Headless Chrome' },
  { pattern: /PhantomJS/i, family: 'PhantomJS' },
  { pattern: /Selenium/i, family: 'Selenium' },
  { pattern: /Puppeteer/i, family: 'Puppeteer' },
  { pattern: /Playwright/i, family: 'Playwright' },
  { pattern: /webdriver/i, family: 'WebDriver' },
];

/**
 * Known crawl bots that are NOT AI agents.
 * These should be excluded from AI detection to avoid false positives.
 */
const KNOWN_CRAWLER_PATTERNS: RegExp[] = [
  /Googlebot/i,
  /Bingbot/i,
  /Slurp/i,           // Yahoo
  /DuckDuckBot/i,
  /Baiduspider/i,
  /YandexBot/i,
  /Sogou/i,
  /Exabot/i,
  /ia_archiver/i,      // Alexa
  /MJ12bot/i,          // Majestic
  /AhrefsBot/i,
  /SemrushBot/i,
  /DotBot/i,
  /rogerbot/i,
  /UptimeRobot/i,
  /PingdomBot/i,
  /StatusCake/i,
];

/**
 * Check the User-Agent string for known AI agent patterns.
 */
export function matchUserAgent(ua?: string): UAMatchResult {
  const userAgent = ua || (typeof navigator !== 'undefined' ? navigator.userAgent : '');

  if (!userAgent) {
    return { matched: false, isCrawler: false };
  }

  // Check if it's a known traditional crawler first
  for (const pattern of KNOWN_CRAWLER_PATTERNS) {
    if (pattern.test(userAgent)) {
      return { matched: false, isCrawler: true };
    }
  }

  // Check for AI agent patterns
  for (const { pattern, family } of AI_AGENT_PATTERNS) {
    if (pattern.test(userAgent)) {
      return { matched: true, agentFamily: family, isCrawler: false };
    }
  }

  return { matched: false, isCrawler: false };
}
