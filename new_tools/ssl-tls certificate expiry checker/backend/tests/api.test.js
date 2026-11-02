const request = require('supertest');
const mongoose = require('mongoose');
const { MongoMemoryServer } = require('mongodb-memory-server');
const app = require('../src/app');
const Lookup = require('../src/db/models/Lookup');
const CertCache = require('../src/db/models/CertCache');
const RateLimit = require('../src/db/models/RateLimit');

let mongoServer;

beforeAll(async () => {
  mongoServer = await MongoMemoryServer.create();
  const uri = mongoServer.getUri();
  await mongoose.connect(uri);
});

afterAll(async () => {
  await mongoose.disconnect();
  if (mongoServer) {
    await mongoServer.stop();
  }
});

beforeEach(async () => {
  await Lookup.deleteMany({});
  await CertCache.deleteMany({});
  await RateLimit.deleteMany({});
});

describe('SSL Checker API Integration Tests', () => {
  test('GET /api/health should return ok status', async () => {
    const res = await request(app).get('/api/health');
    expect(res.statusCode).toBe(200);
    expect(res.body.status).toBe('ok');
    expect(res.body.service).toBe('voidonyx-ssl-checker-api');
    expect(res.body.database).toBe('connected');
  });

  test('POST /api/check should validate invalid host inputs', async () => {
    const res = await request(app)
      .post('/api/check')
      .send({ host: 'invalid_domain!@#' });

    expect(res.statusCode).toBe(400);
    expect(res.body.error).toBe('Invalid input');
  });

  test('POST /api/check should serve cached result when available in MongoDB', async () => {
    const mockHost = 'test-cache.example.com';
    const mockPort = 443;
    const hostPort = `${mockHost}:${mockPort}`;

    const mockCertResult = {
      host: mockHost,
      port: mockPort,
      status: 'valid',
      daysRemaining: 45,
      subject: { cn: mockHost },
      issuer: { cn: 'Test CA' },
      sans: [mockHost],
      fingerprintSha256: 'AA:BB:CC',
      validity: {
        notBefore: new Date().toISOString(),
        notAfter: new Date(Date.now() + 86400000 * 45).toISOString(),
      },
    };

    // Pre-populate CertCache document
    await CertCache.create({
      hostPort,
      host: mockHost,
      port: mockPort,
      result: mockCertResult,
      cachedAt: new Date(),
      expiresAt: new Date(Date.now() + 600000), // 10 mins
    });

    const res = await request(app)
      .post('/api/check')
      .send({ host: mockHost, port: mockPort });

    expect(res.statusCode).toBe(200);
    expect(res.body.isCached).toBe(true);
    expect(res.body.host).toBe(mockHost);
    expect(res.body.daysRemaining).toBe(45);

    // Verify lookup audit log was generated
    const lookups = await Lookup.find({ host: mockHost });
    expect(lookups.length).toBe(1);
    expect(lookups[0].status).toBe('valid');
  });

  test('GET /api/recent should return latest distinct host lookups', async () => {
    await Lookup.create([
      {
        host: 'domain1.com',
        port: 443,
        status: 'valid',
        daysRemaining: 60,
        requesterIpHash: 'hash1',
        checkedAt: new Date(Date.now() - 10000),
      },
      {
        host: 'domain2.com',
        port: 443,
        status: 'expiring',
        daysRemaining: 12,
        requesterIpHash: 'hash2',
        checkedAt: new Date(Date.now() - 5000),
      },
    ]);

    const res = await request(app).get('/api/recent');
    expect(res.statusCode).toBe(200);
    expect(Array.isArray(res.body.recent)).toBe(true);
    expect(res.body.recent.length).toBe(2);
    expect(res.body.recent[0].host).toBe('domain2.com');
  });
});
