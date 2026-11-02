const express = require('express');
const router = express.Router();
const rateLimiter = require('../middleware/rateLimiter');
const { performLookup, getHistory } = require('../services/lookupService');

/**
 * POST /api/whois/lookup
 * Main lookup endpoint with rate limiting
 */
router.post('/whois/lookup', rateLimiter, async (req, res, next) => {
  try {
    const { domain, forceRefresh, sessionId: bodySessionId } = req.body;
    const sessionId = req.headers['x-session-id'] || bodySessionId || null;
    const clientIp = req.headers['x-forwarded-for']?.split(',')[0].trim() || req.socket.remoteAddress || '127.0.0.1';

    if (!domain) {
      return res.status(400).json({
        success: false,
        error: 'Domain parameter is required.',
      });
    }

    const result = await performLookup(domain, clientIp, !!forceRefresh, sessionId);

    if (!result.success) {
      return res.status(400).json({
        success: false,
        error: result.error,
      });
    }

    return res.json({
      success: true,
      data: result.data,
    });
  } catch (err) {
    next(err);
  }
});

/**
 * GET /api/whois/history
 * Returns recent lookups feed (type="my" for browser session history, type="global" for global feed)
 */
router.get('/whois/history', async (req, res, next) => {
  try {
    const limit = parseInt(req.query.limit || '10', 10);
    const type = req.query.type || 'global';
    const sessionId = req.headers['x-session-id'] || req.query.sessionId || null;
    const clientIp = req.headers['x-forwarded-for']?.split(',')[0].trim() || req.socket.remoteAddress || '127.0.0.1';

    const history = await getHistory({
      type,
      sessionId,
      clientIp,
      limit,
    });

    return res.json({
      success: true,
      data: history,
    });
  } catch (err) {
    next(err);
  }
});

/**
 * GET /api/health
 * Health check endpoint
 */
router.get('/health', (req, res) => {
  return res.json({
    status: 'healthy',
    service: 'voidonyx-whois-api',
    uptime: process.uptime(),
    timestamp: new Date().toISOString(),
  });
});

module.exports = router;
