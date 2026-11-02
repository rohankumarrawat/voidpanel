const request = require('supertest');
const mongoose = require('mongoose');
const { MongoMemoryServer } = require('mongodb-memory-server');
const app = require('../src/app');

let mongoServer;

beforeAll(async () => {
  mongoServer = await MongoMemoryServer.create();
  const mongoUri = mongoServer.getUri();
  await mongoose.connect(mongoUri);
});

afterAll(async () => {
  await mongoose.disconnect();
  if (mongoServer) {
    await mongoServer.stop();
  }
});

describe('WHOIS API Endpoints', () => {
  test('GET /api/health returns 200 healthy status', async () => {
    const res = await request(app).get('/api/health');
    expect(res.status).toBe(200);
    expect(res.body.status).toBe('healthy');
  });

  test('POST /api/whois/lookup rejects invalid IP address input', async () => {
    const res = await request(app)
      .post('/api/whois/lookup')
      .send({ domain: '8.8.8.8' });

    expect(res.status).toBe(400);
    expect(res.body.success).toBe(false);
    expect(res.body.error).toContain('IP address provided');
  });

  test('POST /api/whois/lookup returns lookup result for domain', async () => {
    const res = await request(app)
      .post('/api/whois/lookup')
      .send({ domain: 'voidonyx.in' });

    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    expect(res.body.data.domain).toBe('voidonyx.in');
    expect(res.body.data).toHaveProperty('status');
  });

  test('GET /api/whois/history returns recent lookups list', async () => {
    const res = await request(app).get('/api/whois/history');
    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    expect(Array.isArray(res.body.data)).toBe(true);
  });

  test('GET /api/whois/history supports personal vs global history separation', async () => {
    const sessionA = 'test-session-browser-A';
    const sessionB = 'test-session-browser-B';

    // Perform lookup with Session A
    await request(app)
      .post('/api/whois/lookup')
      .set('X-Session-ID', sessionA)
      .send({ domain: 'google.com' });

    // Fetch personal history for Session A
    const resA = await request(app)
      .get('/api/whois/history?type=my')
      .set('X-Session-ID', sessionA);

    expect(resA.status).toBe(200);
    expect(resA.body.data.some((d) => d.domain === 'google.com')).toBe(true);

    // Fetch personal history for Session B (should not contain google.com unless global)
    const resB = await request(app)
      .get('/api/whois/history?type=my')
      .set('X-Session-ID', sessionB);

    expect(resB.status).toBe(200);
    expect(resB.body.data.some((d) => d.domain === 'google.com')).toBe(false);

    // Fetch global history (should contain google.com)
    const resGlobal = await request(app).get('/api/whois/history?type=global');
    expect(resGlobal.status).toBe(200);
    expect(resGlobal.body.data.some((d) => d.domain === 'google.com')).toBe(true);
  });
});
