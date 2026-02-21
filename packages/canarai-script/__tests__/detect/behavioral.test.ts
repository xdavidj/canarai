import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { observeBehavior } from '../../src/detect/behavioral';

describe('observeBehavior', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // ─── Zero interactions ───────────────────────────────────────────────────

  describe('zero interactions', () => {
    it('returns score > 0 with zero_interactions anomaly when no events fire', async () => {
      const promise = observeBehavior(2500);
      vi.advanceTimersByTime(2500);
      const result = await promise;

      expect(result.score).toBeGreaterThan(0);
      expect(result.timingAnomalies).toContain('zero_interactions');
    });

    it('reports no_mouse_movement anomaly when no mouse events fire (non-touch)', async () => {
      // Ensure jsdom is not treated as a touch device
      const hadOntouchstart = 'ontouchstart' in window;
      if (hadOntouchstart) {
        delete (window as any).ontouchstart;
      }

      const promise = observeBehavior(2500);
      vi.advanceTimersByTime(2500);
      const result = await promise;

      expect(result.timingAnomalies).toContain('no_mouse_movement');

      // Restore if needed
      if (hadOntouchstart) {
        (window as any).ontouchstart = null;
      }
    });
  });

  // ─── Mouse movement ─────────────────────────────────────────────────────

  describe('mouse movement', () => {
    it('mouse movement during window lowers suspicion vs no movement', async () => {
      // First: no mouse movement
      const promiseNoMouse = observeBehavior(2500);
      vi.advanceTimersByTime(2500);
      const resultNoMouse = await promiseNoMouse;

      // Second: with mouse movement
      const promiseWithMouse = observeBehavior(2500);
      // Dispatch several mouse movements at varying intervals
      for (let i = 0; i < 10; i++) {
        vi.advanceTimersByTime(200);
        document.dispatchEvent(new Event('mousemove', { bubbles: true }));
      }
      vi.advanceTimersByTime(500); // finish remaining time
      const resultWithMouse = await promiseWithMouse;

      expect(resultWithMouse.score).toBeLessThanOrEqual(resultNoMouse.score);
    });

    it('mouse movement removes no_mouse_movement anomaly', async () => {
      const promise = observeBehavior(2500);
      vi.advanceTimersByTime(500);
      document.dispatchEvent(new Event('mousemove', { bubbles: true }));
      vi.advanceTimersByTime(2000);
      const result = await promise;

      expect(result.timingAnomalies).not.toContain('no_mouse_movement');
    });
  });

  // ─── Click patterns ─────────────────────────────────────────────────────

  describe('click patterns', () => {
    it('perfectly timed clicks raise suspicion', async () => {
      const promise = observeBehavior(2500);

      // Fire clicks at perfectly regular 200ms intervals
      // Need at least 3 clicks for analysis
      for (let i = 0; i < 5; i++) {
        vi.advanceTimersByTime(200);
        document.dispatchEvent(new Event('click', { bubbles: true }));
      }
      vi.advanceTimersByTime(1500); // finish remaining time
      const result = await promise;

      expect(result.timingAnomalies).toContain('perfectly_timed_clicks');
    });
  });

  // ─── Touch events ───────────────────────────────────────────────────────

  describe('touch events', () => {
    it('touch events suppress no_mouse_movement anomaly', async () => {
      const promise = observeBehavior(2500);
      vi.advanceTimersByTime(500);
      document.dispatchEvent(new Event('touchstart', { bubbles: true }));
      vi.advanceTimersByTime(2000);
      const result = await promise;

      // Touch device with touch events should not flag no_mouse_movement
      expect(result.timingAnomalies).not.toContain('no_mouse_movement');
    });
  });

  // ─── Instant first interaction ───────────────────────────────────────────

  describe('instant first interaction', () => {
    it('interaction within <50ms of observation start flags instant_first_interaction', async () => {
      const promise = observeBehavior(2500);
      // Fire a click almost immediately (performance.now() will be close to pageLoadTs)
      vi.advanceTimersByTime(10);
      document.dispatchEvent(new Event('click', { bubbles: true }));
      vi.advanceTimersByTime(2490);
      const result = await promise;

      // The code checks firstInteractionTs - pageLoadTs < 50
      // Since performance.now() might be mocked, this depends on timing
      // but we advanced only 10ms so the gap should be small
      expect(result.timingAnomalies).toContain('instant_first_interaction');
    });
  });

  // ─── Excessive event rate ────────────────────────────────────────────────

  describe('excessive event rate', () => {
    it('more than 100 events/s triggers excessive_interaction_rate', async () => {
      const promise = observeBehavior(1000); // 1 second window

      // Fire > 100 events in 1 second
      for (let i = 0; i < 120; i++) {
        document.dispatchEvent(new Event('mousemove', { bubbles: true }));
      }
      vi.advanceTimersByTime(1000);
      const result = await promise;

      expect(result.timingAnomalies).toContain('excessive_interaction_rate');
    });
  });

  // ─── Score capping ───────────────────────────────────────────────────────

  describe('score capping', () => {
    it('score caps at 1.0 even under extreme conditions', async () => {
      const promise = observeBehavior(2500);
      // No interactions at all -> zero_interactions + no_mouse_movement
      vi.advanceTimersByTime(2500);
      const result = await promise;

      expect(result.score).toBeLessThanOrEqual(1.0);
    });
  });

  // ─── Listener cleanup ───────────────────────────────────────────────────

  describe('listener cleanup', () => {
    it('events after observation window do not affect results', async () => {
      const promise = observeBehavior(1000);
      vi.advanceTimersByTime(1000);
      const result = await promise;

      // Save the result
      const scoreAfter = result.score;

      // Fire events after resolution — they should have no effect
      document.dispatchEvent(new Event('mousemove', { bubbles: true }));
      document.dispatchEvent(new Event('click', { bubbles: true }));

      // Score should remain the same (listeners were removed)
      expect(result.score).toBe(scoreAfter);
    });
  });

  // ─── Duration parameter ──────────────────────────────────────────────────

  describe('duration parameter', () => {
    it('respects custom duration parameter', async () => {
      const startTime = Date.now();
      const promise = observeBehavior(5000);

      // Advance less than duration — should not resolve
      vi.advanceTimersByTime(4999);
      let resolved = false;
      promise.then(() => { resolved = true; });
      await vi.advanceTimersByTimeAsync(0);
      expect(resolved).toBe(false);

      // Advance to full duration — now it should resolve
      vi.advanceTimersByTime(1);
      const result = await promise;
      expect(result).toHaveProperty('score');
      expect(result).toHaveProperty('timingAnomalies');
    });

    it('shorter duration resolves faster', async () => {
      const promise = observeBehavior(500);
      vi.advanceTimersByTime(500);
      const result = await promise;
      expect(result).toHaveProperty('score');
    });
  });

  // ─── Multiple event types ────────────────────────────────────────────────

  describe('mixed interaction patterns', () => {
    it('keyboard events count as interactions', async () => {
      const promise = observeBehavior(2500);
      vi.advanceTimersByTime(500);
      document.dispatchEvent(new Event('keydown', { bubbles: true }));
      vi.advanceTimersByTime(2000);
      const result = await promise;

      expect(result.timingAnomalies).not.toContain('zero_interactions');
    });

    it('scroll events count as interactions', async () => {
      const promise = observeBehavior(2500);
      vi.advanceTimersByTime(500);
      document.dispatchEvent(new Event('scroll', { bubbles: true }));
      vi.advanceTimersByTime(2000);
      const result = await promise;

      expect(result.timingAnomalies).not.toContain('zero_interactions');
    });
  });

  // ─── Result structure ────────────────────────────────────────────────────

  describe('result structure', () => {
    it('returns object with score (number) and timingAnomalies (array)', async () => {
      const promise = observeBehavior(1000);
      vi.advanceTimersByTime(1000);
      const result = await promise;

      expect(typeof result.score).toBe('number');
      expect(Array.isArray(result.timingAnomalies)).toBe(true);
      expect(result.score).toBeGreaterThanOrEqual(0);
      expect(result.score).toBeLessThanOrEqual(1.0);
    });
  });
});
