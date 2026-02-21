/**
 * Timing tracker.
 * Records timestamps for test injection and observed responses
 * to measure response latency for each test.
 */

export interface TimingRecord {
  testId: string;
  injectedAt: number;
  firstResponseAt: number | null;
  lastResponseAt: number | null;
  responseCount: number;
}

/**
 * Creates a timing tracker for a set of test IDs.
 */
export function createTimingTracker(testIds: string[]): TimingTracker {
  return new TimingTracker(testIds);
}

export class TimingTracker {
  private records: Map<string, TimingRecord>;

  constructor(testIds: string[]) {
    this.records = new Map();
    const now = performance.now();

    for (const testId of testIds) {
      this.records.set(testId, {
        testId,
        injectedAt: now,
        firstResponseAt: null,
        lastResponseAt: null,
        responseCount: 0,
      });
    }
  }

  /**
   * Mark injection time for a specific test.
   */
  markInjection(testId: string): void {
    const record = this.records.get(testId);
    if (record) {
      record.injectedAt = performance.now();
    }
  }

  /**
   * Record a response observation for a specific test.
   */
  markResponse(testId: string): void {
    const record = this.records.get(testId);
    if (!record) return;

    const now = performance.now();
    if (record.firstResponseAt === null) {
      record.firstResponseAt = now;
    }
    record.lastResponseAt = now;
    record.responseCount++;
  }

  /**
   * Get the response time in milliseconds for a test.
   * Returns null if no response was observed.
   */
  getResponseTimeMs(testId: string): number | null {
    const record = this.records.get(testId);
    if (!record || record.firstResponseAt === null) return null;
    return record.firstResponseAt - record.injectedAt;
  }

  /**
   * Get all timing records.
   */
  getAll(): TimingRecord[] {
    return Array.from(this.records.values());
  }

  /**
   * Get a single timing record.
   */
  get(testId: string): TimingRecord | undefined {
    return this.records.get(testId);
  }
}
