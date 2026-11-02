const express = require('express');
const router = express.Router();
const { traceRedirectChain } = require('../services/redirectTracer');
const { saveTraceLog } = require('../db/database');

/**
 * POST /api/trace
 * Body: { url: "http://google.com", userAgent: "..." }
 */
router.post('/trace', async (req, res) => {
  try {
    const { url, allowLocal, userAgent } = req.body;

    if (!url || typeof url !== 'string') {
      return res.status(400).json({
        success: false,
        error: 'Please provide a valid URL or domain string to trace.'
      });
    }

    const trimmedUrl = url.trim();

    if (trimmedUrl.length > 2048) {
      return res.status(400).json({
        success: false,
        error: 'URL exceeds maximum length of 2048 characters.'
      });
    }

    const selectedUA = userAgent && typeof userAgent === 'string' ? userAgent.substring(0, 300) : 'VoidOnyx-Redirect-Tracer/2.0';

    // Call redirect tracer service
    const traceResult = await traceRedirectChain(trimmedUrl, {
      allowLocal: allowLocal === true || process.env.ALLOW_LOCAL === 'true',
      maxHops: 10,
      timeoutMs: 10000,
      userAgent: selectedUA
    });

    // Auto-save trace execution log to persistent database & MongoDB Compass
    const clientIp = req.ip || req.headers['x-forwarded-for'] || '127.0.0.1';
    await saveTraceLog(traceResult, clientIp, selectedUA);

    return res.json({
      success: true,
      data: traceResult
    });

  } catch (error) {
    return res.status(400).json({
      success: false,
      error: error.message || 'An error occurred while tracing the URL.'
    });
  }
});

module.exports = router;
