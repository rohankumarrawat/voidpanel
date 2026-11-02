const request = require('supertest');
const app = require('../server');
const { isPrivateHost } = require('../services/redirectTracer');
const { analyzeHeaders } = require('../services/securityHeaderAnalyzer');
const mongoose = require('mongoose');

jest.setTimeout(15000);

describe('HTTP Header & Redirect Tracer Backend Engine', () => {

  afterAll(async () => {
    if (mongoose.connection.readyState !== 0) {
      await mongoose.disconnect();
    }
  });

  describe('SSRF Protection (isPrivateHost)', () => {
    test('identifies loopback and private IPv4 addresses correctly', () => {
      expect(isPrivateHost('127.0.0.1')).toBe(true);
      expect(isPrivateHost('localhost')).toBe(true);
      expect(isPrivateHost('10.0.0.1')).toBe(true);
      expect(isPrivateHost('192.168.1.100')).toBe(true);
      expect(isPrivateHost('172.16.0.1')).toBe(true);
    });

    test('allows public domains and public IPs', () => {
      expect(isPrivateHost('google.com')).toBe(false);
      expect(isPrivateHost('8.8.8.8')).toBe(false);
      expect(isPrivateHost('1.1.1.1')).toBe(false);
    });

    test('bypasses checks when allowLocal is true', () => {
      expect(isPrivateHost('127.0.0.1', true)).toBe(false);
      expect(isPrivateHost('localhost', true)).toBe(false);
    });
  });

  describe('Security Header Analyzer (analyzeHeaders)', () => {
    test('grades secure header set with A/A+', () => {
      const headers = {
        'strict-transport-security': 'max-age=31536000; includeSubDomains; preload',
        'content-security-policy': "default-src 'self'",
        'x-frame-options': 'DENY',
        'x-content-type-options': 'nosniff',
        'referrer-policy': 'strict-origin-when-cross-origin',
        'permissions-policy': 'camera=()'
      };

      const result = analyzeHeaders(headers, 'https:');
      expect(result.score).toBeGreaterThanOrEqual(90);
      expect(['A', 'A+']).toContain(result.grade);
      expect(result.summaryCounts.fail).toBe(0);
    });

    test('flags missing HSTS and CSP headers', () => {
      const headers = {
        'x-content-type-options': 'nosniff'
      };

      const result = analyzeHeaders(headers, 'https:');
      expect(result.score).toBeLessThan(50);
      const hstsAudit = result.audits.find(a => a.header === 'Strict-Transport-Security');
      const cspAudit = result.audits.find(a => a.header === 'Content-Security-Policy');

      expect(hstsAudit.status).toBe('FAIL');
      expect(cspAudit.status).toBe('FAIL');
    });
  });

  describe('API Endpoint POST /api/trace', () => {
    test('rejects empty payload with 400 status', async () => {
      const res = await request(app)
        .post('/api/trace')
        .send({});

      expect(res.statusCode).toBe(400);
      expect(res.body.success).toBe(false);
      expect(res.body.error).toContain('valid URL');
    });

    test('rejects local IP access by default with SSRF protection error', async () => {
      const res = await request(app)
        .post('/api/trace')
        .send({ url: 'http://127.0.0.1:3001' });

      expect(res.statusCode).toBe(400);
      expect(res.body.success).toBe(false);
      expect(res.body.error).toContain('Access restricted');
    });
  });

});
