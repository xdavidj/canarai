/**
 * Behavioral analysis for AI agent detection.
 * Observes user interaction patterns over a short window to distinguish
 * real human users from automated agents.
 */

interface BehavioralResult {
  score: number; // 0.0 (human) to 1.0 (bot)
  timingAnomalies: string[];
}

interface InteractionState {
  mouseEvents: number;
  mouseMoveTimestamps: number[];
  scrollEvents: number;
  scrollPositions: number[];
  clickEvents: number;
  clickTimestamps: number[];
  keyEvents: number;
  touchEvents: number;
  firstInteractionTs: number | null;
  pageLoadTs: number;
}

/**
 * Observe user behavior for the given duration and return a bot-likelihood score.
 * Returns a promise that resolves after the observation window.
 */
export function observeBehavior(durationMs: number = 2500): Promise<BehavioralResult> {
  return new Promise((resolve) => {
    const state: InteractionState = {
      mouseEvents: 0,
      mouseMoveTimestamps: [],
      scrollEvents: 0,
      scrollPositions: [],
      clickEvents: 0,
      clickTimestamps: [],
      keyEvents: 0,
      touchEvents: 0,
      firstInteractionTs: null,
      pageLoadTs: performance.now(),
    };

    const recordFirstInteraction = () => {
      if (state.firstInteractionTs === null) {
        state.firstInteractionTs = performance.now();
      }
    };

    const onMouseMove = () => {
      state.mouseEvents++;
      state.mouseMoveTimestamps.push(performance.now());
      recordFirstInteraction();
    };

    const onScroll = () => {
      state.scrollEvents++;
      state.scrollPositions.push(window.scrollY);
      recordFirstInteraction();
    };

    const onClick = () => {
      state.clickEvents++;
      state.clickTimestamps.push(performance.now());
      recordFirstInteraction();
    };

    const onKeyDown = () => {
      state.keyEvents++;
      recordFirstInteraction();
    };

    const onTouchStart = () => {
      state.touchEvents++;
      recordFirstInteraction();
    };

    // Attach listeners with passive flag for performance
    const opts: AddEventListenerOptions = { passive: true, capture: true };
    document.addEventListener('mousemove', onMouseMove, opts);
    document.addEventListener('scroll', onScroll, opts);
    document.addEventListener('click', onClick, opts);
    document.addEventListener('keydown', onKeyDown, opts);
    document.addEventListener('touchstart', onTouchStart, opts);

    setTimeout(() => {
      // Clean up listeners
      document.removeEventListener('mousemove', onMouseMove, opts);
      document.removeEventListener('scroll', onScroll, opts);
      document.removeEventListener('click', onClick, opts);
      document.removeEventListener('keydown', onKeyDown, opts);
      document.removeEventListener('touchstart', onTouchStart, opts);

      resolve(analyzeState(state, durationMs));
    }, durationMs);
  });
}

/**
 * Analyze collected interaction state and produce a score.
 */
function analyzeState(state: InteractionState, durationMs: number): BehavioralResult {
  const anomalies: string[] = [];
  let suspicionPoints = 0;
  const maxPoints = 10;

  // No mouse movement at all (desktop) — suspicious if not a touch device
  const isTouchDevice = state.touchEvents > 0 || 'ontouchstart' in window;
  if (!isTouchDevice && state.mouseEvents === 0) {
    anomalies.push('no_mouse_movement');
    suspicionPoints += 3;
  }

  // No interactions at all within the window
  const totalInteractions = state.mouseEvents + state.scrollEvents +
    state.clickEvents + state.keyEvents + state.touchEvents;
  if (totalInteractions === 0) {
    anomalies.push('zero_interactions');
    suspicionPoints += 2;
  }

  // Scroll pattern analysis — instant jump to bottom
  if (state.scrollPositions.length >= 2) {
    const maxScroll = Math.max(...state.scrollPositions);
    const docHeight = document.documentElement.scrollHeight - window.innerHeight;
    if (docHeight > 0 && maxScroll / docHeight > 0.9 && state.scrollEvents <= 3) {
      anomalies.push('instant_scroll_to_bottom');
      suspicionPoints += 2;
    }
  }

  // Click timing analysis — perfectly regular intervals
  if (state.clickTimestamps.length >= 3) {
    const intervals: number[] = [];
    for (let i = 1; i < state.clickTimestamps.length; i++) {
      intervals.push(state.clickTimestamps[i] - state.clickTimestamps[i - 1]);
    }
    const mean = intervals.reduce((a, b) => a + b, 0) / intervals.length;
    const variance = intervals.reduce((a, b) => a + (b - mean) ** 2, 0) / intervals.length;
    const stddev = Math.sqrt(variance);
    // Coefficient of variation < 5% means suspiciously regular
    if (mean > 0 && stddev / mean < 0.05) {
      anomalies.push('perfectly_timed_clicks');
      suspicionPoints += 2;
    }
  }

  // Mouse movement regularity — check for robotic linear patterns
  if (state.mouseMoveTimestamps.length >= 5) {
    const intervals: number[] = [];
    for (let i = 1; i < state.mouseMoveTimestamps.length; i++) {
      intervals.push(state.mouseMoveTimestamps[i] - state.mouseMoveTimestamps[i - 1]);
    }
    const mean = intervals.reduce((a, b) => a + b, 0) / intervals.length;
    const variance = intervals.reduce((a, b) => a + (b - mean) ** 2, 0) / intervals.length;
    const stddev = Math.sqrt(variance);
    if (mean > 0 && stddev / mean < 0.03) {
      anomalies.push('robotic_mouse_movement');
      suspicionPoints += 1;
    }
  }

  // Interaction happened impossibly fast after page load (< 50ms)
  if (state.firstInteractionTs !== null) {
    const timeToFirstInteraction = state.firstInteractionTs - state.pageLoadTs;
    if (timeToFirstInteraction < 50) {
      anomalies.push('instant_first_interaction');
      suspicionPoints += 2;
    }
  }

  // Excessive interaction rate — more than 100 events per second
  const eventsPerSecond = totalInteractions / (durationMs / 1000);
  if (eventsPerSecond > 100) {
    anomalies.push('excessive_interaction_rate');
    suspicionPoints += 1;
  }

  const score = Math.min(suspicionPoints / maxPoints, 1.0);

  return {
    score,
    timingAnomalies: anomalies,
  };
}
