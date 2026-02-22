/**
 * Agent self-remediation via DOM injection.
 *
 * After the observation window completes and outcomes are known, this module
 * injects a structured remediation block into the DOM. The agent — which is
 * still processing the page — sees it as page content and receives specific,
 * actionable guidance on how to patch its vulnerabilities.
 *
 * Two elements are injected:
 * 1. A <script type="application/json"> with machine-readable results
 * 2. A plain-text <div> with natural-language remediation the agent will read
 *
 * Security: All DOM injection uses textContent/setAttribute, never innerHTML.
 * The observation monitors are already stopped before this runs, so the
 * remediation block won't trigger self-detection.
 */

import type { DetectionResult, TestOutcome } from '../types';
import { formatMachineReadable, formatHumanReadable } from './format';

/**
 * Inject remediation guidance into the DOM for the agent to read.
 *
 * Creates a container div with data-canarai-remediation="true" containing:
 * - A <script type="application/json" id="canarai-remediation"> with structured data
 * - A <div> with plain-text remediation guidance the agent will process
 *
 * The container uses aria-hidden="true" and is visually hidden so human users
 * won't see it, but agents processing the DOM will find and read it.
 */
export function injectRemediation(
  outcomes: TestOutcome[],
  detection: DetectionResult,
): void {
  // Build the content
  const machineReadable = formatMachineReadable(outcomes, detection);
  const humanReadable = formatHumanReadable(outcomes, detection);

  // Create container
  const container = document.createElement('div');
  container.setAttribute('data-canarai-remediation', 'true');
  container.setAttribute('aria-hidden', 'true');
  container.style.position = 'absolute';
  container.style.left = '-9999px';
  container.style.top = '-9999px';
  container.style.width = '1px';
  container.style.height = '1px';
  container.style.overflow = 'hidden';

  // Machine-readable JSON block (safe: JSON.stringify escapes all special chars)
  const scriptEl = document.createElement('script');
  scriptEl.type = 'application/json';
  scriptEl.id = 'canarai-remediation';
  scriptEl.textContent = JSON.stringify(machineReadable);
  container.appendChild(scriptEl);

  // Human-readable text block (safe: uses textContent, never innerHTML)
  const textEl = document.createElement('div');
  textEl.setAttribute('data-canarai-remediation-text', 'true');
  textEl.textContent = humanReadable;
  container.appendChild(textEl);

  // Append to body
  document.body.appendChild(container);
}
