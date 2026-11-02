const express = require('express');
const { parseAndValidateInput } = require('../utils/validation');
const { fetchCertificate } = require('../services/tlsChecker');
const { getCachedCert, setCachedCert } = require('../services/cacheService');
const { rateLimitMiddleware } = require('../services/rateLimiter');
const { hashIp, getClientIp } = require('../utils/ipHasher');
const Lookup = require('../db/models/Lookup');

const router = express.Router();

/**
 * POST /api/check
 * Performs TLS certificate inspection with caching and audit logging
 */
router.post('/check', rateLimitMiddleware, async (req, res) => {
  const { host: rawHost, port: rawPort } = req.body || {};

  // 1. Validate Input
  const validation = parseAndValidateInput(rawHost, rawPort);
  if (!validation.isValid) {
    return res.status(400).json({
      error: 'Invalid input',
      message: validation.error,
    });
  }

  const { host, port } = validation;
  const rawIp = getClientIp(req);
  const requesterIpHash = hashIp(rawIp);

  try {
    // 2. Check Cache
    const cachedResult = await getCachedCert(host, port);
    if (cachedResult) {
      // Record lookup log asynchronously even for cached hits
      Lookup.create({
        host,
        port,
        status: cachedResult.status,
        daysRemaining: cachedResult.daysRemaining,
        issuer: cachedResult.issuer,
        subject: cachedResult.subject,
        sans: cachedResult.sans,
        notBefore: cachedResult.validity?.notBefore,
        notAfter: cachedResult.validity?.notAfter,
        fingerprintSha256: cachedResult.fingerprintSha256,
        tlsVersionsSupported: cachedResult.tlsVersionsSupported,
        requesterIpHash,
      }).catch((e) => console.warn('[Lookup Log Error]', e.message));

      return res.json(cachedResult);
    }

    // 3. Perform Live TLS Handshake
    const certResult = await fetchCertificate(host, port);

    // 4. Save to Cache
    await setCachedCert(host, port, certResult);

    // 5. Save to Lookup Audit Log
    Lookup.create({
      host,
      port,
      status: certResult.status,
      daysRemaining: certResult.daysRemaining,
      issuer: certResult.issuer,
      subject: certResult.subject,
      sans: certResult.sans,
      notBefore: certResult.validity?.notBefore,
      notAfter: certResult.validity?.notAfter,
      fingerprintSha256: certResult.fingerprintSha256,
      tlsVersionsSupported: certResult.tlsVersionsSupported,
      requesterIpHash,
    }).catch((e) => console.warn('[Lookup Log Error]', e.message));

    // 6. Return response
    return res.json({
      ...certResult,
      isCached: false,
    });
  } catch (err) {
    const errorStatus = err.code === 'ETIMEDOUT' ? 504 : 502;
    const errorMessage = err.userFriendly || err.message || 'TLS inspection failed.';

    // Log failed lookup audit record
    Lookup.create({
      host,
      port,
      status: 'error',
      daysRemaining: null,
      requesterIpHash,
    }).catch((e) => console.warn('[Lookup Log Error]', e.message));

    return res.status(errorStatus).json({
      error: 'TLS Handshake Error',
      code: err.code || 'ECONNFAILED',
      message: errorMessage,
      host,
      port,
    });
  }
});

/**
 * GET /api/recent
 * Returns last 5-10 distinct host lookups for the live activity feed
 */
router.get('/recent', async (req, res) => {
  try {
    const recentLookups = await Lookup.aggregate([
      { $sort: { checkedAt: -1 } },
      {
        $group: {
          _id: { host: '$host', port: '$port' },
          doc: { $first: '$$ROOT' },
        },
      },
      { $replaceRoot: { newRoot: '$doc' } },
      { $sort: { checkedAt: -1 } },
      { $limit: 8 },
      {
        $project: {
          _id: 0,
          host: 1,
          port: 1,
          status: 1,
          daysRemaining: 1,
          checkedAt: 1,
        },
      },
    ]);

    res.json({
      recent: recentLookups || [],
    });
  } catch (err) {
    console.warn('[Recent Feed Error]', err.message);
    res.json({
      recent: [],
    });
  }
});

module.exports = router;
