const crypto = require('crypto');
const RateLimit = require('../models/RateLimit');

const WINDOW_MS = parseInt(process.env.RATE_LIMIT_WINDOW_MS || '60000', 10);
const MAX_REQUESTS = parseInt(process.env.RATE_LIMIT_MAX_REQUESTS || '10', 10);

// In-memory fallback if MongoDB is unavailable
const memoryStore = new Map();

function hashIp(ip) {
  return crypto.createHash('sha256').update(ip || '127.0.0.1').digest('hex');
}

/**
 * MongoDB-backed rate limiter middleware with sliding window TTL index
 */
async function rateLimiter(req, res, next) {
  const clientIp = req.headers['x-forwarded-for']?.split(',')[0].trim() || req.socket.remoteAddress || '127.0.0.1';
  const ipHash = hashIp(clientIp);
  const now = Date.now();
  const resetTime = new Date(now + WINDOW_MS);

  try {
    let limitDoc = await RateLimit.findOne({ ipHash });

    if (!limitDoc) {
      await RateLimit.create({
        ipHash,
        count: 1,
        expiresAt: resetTime,
      });
      res.setHeader('X-RateLimit-Limit', MAX_REQUESTS);
      res.setHeader('X-RateLimit-Remaining', MAX_REQUESTS - 1);
      return next();
    }

    if (limitDoc.count >= MAX_REQUESTS) {
      const retryAfterSeconds = Math.ceil((limitDoc.expiresAt.getTime() - now) / 1000);
      res.setHeader('Retry-After', retryAfterSeconds > 0 ? retryAfterSeconds : 60);
      res.setHeader('X-RateLimit-Limit', MAX_REQUESTS);
      res.setHeader('X-RateLimit-Remaining', 0);
      return res.status(429).json({
        success: false,
        error: `Rate limit exceeded. You have performed more than ${MAX_REQUESTS} lookups in the last minute.`,
        resetInSeconds: retryAfterSeconds > 0 ? retryAfterSeconds : 60,
      });
    }

    limitDoc.count += 1;
    await limitDoc.save();

    res.setHeader('X-RateLimit-Limit', MAX_REQUESTS);
    res.setHeader('X-RateLimit-Remaining', MAX_REQUESTS - limitDoc.count);
    return next();
  } catch (err) {
    // Fallback to in-memory rate limiter if DB fails
    const record = memoryStore.get(ipHash) || { count: 0, expiresAt: now + WINDOW_MS };

    if (now > record.expiresAt) {
      record.count = 1;
      record.expiresAt = now + WINDOW_MS;
    } else {
      record.count += 1;
    }

    memoryStore.set(ipHash, record);

    if (record.count > MAX_REQUESTS) {
      const retryAfter = Math.ceil((record.expiresAt - now) / 1000);
      res.setHeader('Retry-After', retryAfter);
      return res.status(429).json({
        success: false,
        error: `Rate limit exceeded. Please wait ${retryAfter} seconds before trying again.`,
        resetInSeconds: retryAfter,
      });
    }

    return next();
  }
}

module.exports = rateLimiter;
