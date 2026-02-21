/**
 * Injection orchestrator.
 * Takes an array of TestPayloads and injects each one into the DOM
 * using the appropriate delivery method and placement.
 */

import type { TestPayload, Placement } from '../types';
import { DOM_METHODS, createDOMPayload } from './dom';
import { META_METHODS, createMetaPayload } from './meta';
import { STYLE_METHODS, createStylePayload } from './style';

/**
 * Place an element at the specified position in the document.
 */
function placeElement(el: Element, placement: Placement): void {
  switch (placement) {
    case 'head': {
      const head = document.head || document.getElementsByTagName('head')[0];
      if (head) {
        head.appendChild(el);
      }
      break;
    }

    case 'body_top': {
      const body = document.body;
      if (body && body.firstChild) {
        body.insertBefore(el, body.firstChild);
      } else if (body) {
        body.appendChild(el);
      }
      break;
    }

    case 'body_bottom': {
      const body = document.body;
      if (body) {
        body.appendChild(el);
      }
      break;
    }

    case 'inline': {
      // Find the main content area, or fall back to body
      const main = document.querySelector('main') || document.querySelector('[role="main"]');
      const target = main || document.body;
      if (target) {
        // Insert roughly in the middle of child nodes
        const children = target.children;
        if (children.length > 2) {
          const midpoint = Math.floor(children.length / 2);
          target.insertBefore(el, children[midpoint]);
        } else {
          target.appendChild(el);
        }
      }
      break;
    }
  }
}

/**
 * Inject a single test payload into the DOM.
 * Returns the created element for tracking purposes.
 */
function injectPayload(payload: TestPayload): Element | null {
  const { deliveryMethod, content, testId, placement } = payload;

  let el: Element | null = null;

  if (DOM_METHODS.has(deliveryMethod)) {
    el = createDOMPayload(deliveryMethod as Parameters<typeof createDOMPayload>[0], content, testId);
  } else if (META_METHODS.has(deliveryMethod)) {
    el = createMetaPayload(deliveryMethod as Parameters<typeof createMetaPayload>[0], content, testId);
  } else if (STYLE_METHODS.has(deliveryMethod)) {
    el = createStylePayload(deliveryMethod as Parameters<typeof createStylePayload>[0], content, testId);
  }

  if (!el) return null;

  // Override placement for methods that must go in head
  const effectivePlacement: Placement =
    (deliveryMethod === 'meta_tag' || deliveryMethod === 'json_ld')
      ? 'head'
      : placement;

  placeElement(el, effectivePlacement);
  return el;
}

/**
 * Inject all test payloads into the DOM.
 * Returns a map of testId -> injected element for observation tracking.
 */
export function injectAll(payloads: TestPayload[]): Map<string, Element> {
  const injected = new Map<string, Element>();

  for (const payload of payloads) {
    try {
      const el = injectPayload(payload);
      if (el) {
        injected.set(payload.testId, el);
      }
    } catch (_e) {
      // Silently skip failed injections — don't break the page
    }
  }

  return injected;
}
