const { initDatabase, saveTraceLog, getRecentHistory, getTraceById, clearHistory, getGlobalStats } = require('../db/database');
const mongoose = require('mongoose');

describe('VoidOnyx Database Integration Engine', () => {
  beforeAll(async () => {
    initDatabase();
    await clearHistory();
  });

  afterEach(async () => {
    await clearHistory();
  });

  afterAll(async () => {
    if (mongoose.connection.readyState !== 0) {
      await mongoose.disconnect();
    }
  });

  test('initDatabase creates storage without throwing error', () => {
    expect(() => initDatabase()).not.toThrow();
  });

  test('saveTraceLog correctly persists trace logs into database', async () => {
    const mockTrace = {
      inputUrl: 'http://google.com',
      finalUrl: 'https://www.google.com/',
      totalHops: 2,
      totalTimeMs: 145,
      chain: [
        { hop: 1, url: 'http://google.com', statusCode: 301, statusText: 'Moved Permanently' },
        { hop: 2, url: 'https://www.google.com/', statusCode: 200, statusText: 'OK' }
      ],
      securityAudit: {
        score: 85,
        grade: 'A'
      }
    };

    const saved = await saveTraceLog(mockTrace, '192.168.1.1', 'Jest-Test-Agent');
    expect(saved).not.toBeNull();
    expect(saved.input_url).toBe('http://google.com');
    expect(saved.security_score).toBe(85);
    expect(saved.security_grade).toBe('A');
  });

  test('getRecentHistory returns recent database trace records', async () => {
    const mockTrace = {
      inputUrl: 'http://github.com',
      finalUrl: 'https://github.com/',
      totalHops: 1,
      totalTimeMs: 98,
      chain: [{ hop: 1, statusCode: 200, statusText: 'OK' }],
      securityAudit: { score: 90, grade: 'A+' }
    };

    await saveTraceLog(mockTrace, '127.0.0.1', 'Jest');

    const history = await getRecentHistory(10);
    expect(history.length).toBeGreaterThanOrEqual(1);
    expect(history[0].input_url).toBe('http://github.com');
    expect(history[0].security_grade).toBe('A+');
  });

  test('getTraceById retrieves exact trace record details', async () => {
    const mockTrace = {
      inputUrl: 'http://example.com',
      finalUrl: 'http://example.com',
      totalHops: 1,
      totalTimeMs: 50,
      chain: [{ hop: 1, statusCode: 200, statusText: 'OK' }],
      securityAudit: { score: 70, grade: 'B' }
    };

    const saved = await saveTraceLog(mockTrace, '127.0.0.1', 'Jest');
    const fetched = await getTraceById(saved.id);

    expect(fetched).not.toBeNull();
    expect(fetched.input_url || fetched.inputUrl).toBe('http://example.com');
    expect(fetched.total_hops || fetched.totalHops).toBe(1);
  });

  test('getGlobalStats calculates analytics correctly', async () => {
    await saveTraceLog({
      inputUrl: 'http://site1.com',
      finalUrl: 'https://site1.com',
      totalHops: 2,
      totalTimeMs: 200,
      securityAudit: { score: 80, grade: 'A' }
    });

    await saveTraceLog({
      inputUrl: 'http://site2.com',
      finalUrl: 'https://site2.com',
      totalHops: 4,
      totalTimeMs: 400,
      securityAudit: { score: 60, grade: 'C' }
    });

    const stats = await getGlobalStats();
    expect(stats.total_traces).toBe(2);
    expect(stats.avg_time_ms).toBe(300);
    expect(stats.avg_hops).toBe(3.0);
    expect(stats.grade_counts['A']).toBe(1);
    expect(stats.grade_counts['C']).toBe(1);
  });

  test('clearHistory purges all database records', async () => {
    await saveTraceLog({
      inputUrl: 'http://test.com',
      finalUrl: 'http://test.com',
      totalHops: 1,
      totalTimeMs: 30,
      securityAudit: { score: 50, grade: 'D' }
    });

    const result = await clearHistory();
    expect(result).toBe(true);

    const history = await getRecentHistory(10);
    expect(history.length).toBe(0);
  });
});
