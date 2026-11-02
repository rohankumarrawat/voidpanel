import express from 'express';
import { validateDomainOrIp } from '../utils/domainValidator.js';
import {
  analyzeSpf,
  analyzeDkim,
  analyzeDmarc,
  calculateOverallScore,
  DEFAULT_DKIM_SELECTORS,
} from '../services/dnsAnalyzer.js';
import { Scan } from '../models/Scan.js';
import { isMongoConnected } from '../config/db.js';
import { analyzeRateLimiter } from '../middleware/rateLimiter.js';

const router = express.Router();

// Memory store fallback if MongoDB is offline
const memoryHistory = [];

/**
 * POST /api/analyze
 * Body: { domain: string, selectors?: string[] }
 */
router.post('/analyze', analyzeRateLimiter, async (req, res) => {
  const { domain, selectors } = req.body || {};

  const validation = validateDomainOrIp(domain);
  if (!validation.valid) {
    return res.status(400).json({
      error: validation.message,
      kind: 'validation',
    });
  }

  const targetDomain = validation.value;
  const customSelectors = Array.isArray(selectors)
    ? selectors
    : typeof selectors === 'string'
      ? selectors.split(',').map((s) => s.trim()).filter(Boolean)
      : [];

  try {
    const [spf, dkim, dmarc] = await Promise.all([
      analyzeSpf(targetDomain),
      analyzeDkim(targetDomain, customSelectors),
      analyzeDmarc(targetDomain),
    ]);

    const overallScore = calculateOverallScore(spf, dkim, dmarc);
    const timestamp = new Date().toISOString();
    const clientIp = req.ip || req.socket?.remoteAddress || '127.0.0.1';

    const scanResult = {
      domain: targetDomain,
      spf,
      dkim,
      dmarc,
      overallScore,
      timestamp,
    };

    // Save scan to database or memory history
    if (isMongoConnected()) {
      try {
        await Scan.create({
          domain: targetDomain,
          overallScore,
          spf,
          dkim,
          dmarc,
          clientIp,
          timestamp: new Date(timestamp),
        });
      } catch (dbErr) {
        console.warn(`[API] Failed to persist scan to MongoDB: ${dbErr.message}`);
      }
    } else {
      memoryHistory.unshift(scanResult);
      if (memoryHistory.length > 50) memoryHistory.pop();
    }

    return res.json(scanResult);
  } catch (error) {
    console.error('[API Error /api/analyze]', error);
    const isTimeout = error.code === 'ETIMEDOUT' || (error.message && error.message.includes('timed out'));
    return res.status(isTimeout ? 504 : 500).json({
      error: isTimeout
        ? `DNS query timed out for domain ${targetDomain}. Please try again.`
        : `Analysis failed: ${error.message || 'DNS resolution error'}`,
      kind: isTimeout ? 'timeout' : 'dns_error',
    });
  }
});

/**
 * GET /api/history?domain=example.com
 */
router.get('/history', async (req, res) => {
  const filterDomain = req.query.domain ? req.query.domain.trim().toLowerCase() : null;

  try {
    if (isMongoConnected()) {
      const query = filterDomain ? { domain: filterDomain } : {};
      const scans = await Scan.find(query).sort({ createdAt: -1 }).limit(20).lean();
      return res.json({
        source: 'database',
        count: scans.length,
        scans,
      });
    } else {
      let filtered = memoryHistory;
      if (filterDomain) {
        filtered = memoryHistory.filter((s) => s.domain.toLowerCase() === filterDomain);
      }
      return res.json({
        source: 'memory_fallback',
        count: filtered.length,
        scans: filtered.slice(0, 20),
      });
    }
  } catch (error) {
    return res.status(500).json({
      error: 'Failed to retrieve scan history.',
      details: error.message,
    });
  }
});

/**
 * GET /api/default-selectors
 */
router.get('/default-selectors', (req, res) => {
  res.json({
    selectors: DEFAULT_DKIM_SELECTORS,
  });
});

export default router;
