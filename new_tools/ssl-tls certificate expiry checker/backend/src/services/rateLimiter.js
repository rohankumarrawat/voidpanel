const RateLimit = require('../db/models/RateLimit');
const env = require('../config/env');
const { hashIp, getClientIp } = require('../utils/ipHasher');

const memoryRateLimit = new Map();

/**
 * Express middleware for rate-limiting lookups
 */
async function rateLimitMiddleware(req, res, next) {
  const rawIp = getClientIp(req);
  const ipHash = hashIp(rawIp);

  const windowSeconds = env.RATE_LIMIT_WINDOW_SECONDS;
  const maxRequests = env.RATE_LIMIT_MAX_REQUESTS;
  const now = new Date();
  const expiresAt = new Date(now.getTime() + windowSeconds * 1000);

  let allowed = true;
  let remaining = maxRequests - 1;
  let resetInSeconds = windowSeconds;

  try {
    let limitDoc = await RateLimit.findOne({ ipHash });

    if (!limitDoc) {
      await RateLimit.create({
        ipHash,
        count: 1,
        windowStart: now,
        expiresAt,
      });
      remaining = maxRequests - 1;
    } else {
      if (limitDoc.count >= maxRequests) {
        allowed = false;
        remaining = 0;
        resetInSeconds = Math.max(1, Math.ceil((limitDoc.expiresAt.getTime() - now.getTime()) / 1000));
      } else {
        limitDoc.count += 1;
        await limitDoc.save();
        remaining = maxRequests - limitDoc.count;
        resetInSeconds = Math.max(1, Math.ceil((limitDoc.expiresAt.getTime() - now.getTime()) / 1000));
      }
    }
  } catch (err) {
    // Fallback to in-memory rate-limiter if MongoDB is down
    const nowMs = Date.now();
    const record = memoryRateLimit.get(ipHash) || { count: 0, windowStart: nowMs };

    if (nowMs - record.windowStart > windowSeconds * 1000) {
      record.count = 1;
      record.windowStart = nowMs;
    } else {
      record.count += 1;
    }
    memoryRateLimit.set(ipHash, record);

    resetInSeconds = Math.ceil((windowSeconds * 1000 - (nowMs - record.windowStart)) / 1000);
    remaining = Math.max(0, maxRequests - record.count);
    if (record.count > maxRequests) {
      allowed = false;
    }
  }

  res.setHeader('X-RateLimit-Limit', maxRequests);
  res.setHeader('X-RateLimit-Remaining', remaining);
  res.setHeader('X-RateLimit-Reset', Math.floor(Date.now() / 1000) + resetInSeconds);

  if (!allowed) {
    res.setHeader('Retry-After', resetInSeconds);
    return res.status(429).json({
      error: 'Rate limit exceeded',
      message: `Too many requests from your IP. Please wait ${resetInSeconds} seconds before checking another domain.`,
      resetInSeconds,
    });
  }

  next();
}

module.exports = { rateLimitMiddleware };
