const CertCache = require('../db/models/CertCache');
const env = require('../config/env');

// In-memory fallback cache in case MongoDB is unreachable during execution
const memoryCache = new Map();

/**
 * Checks cache for host:port combination
 */
async function getCachedCert(host, port) {
  const hostPort = `${host.toLowerCase()}:${port}`;

  try {
    const doc = await CertCache.findOne({ hostPort });
    if (doc) {
      if (doc.expiresAt && doc.expiresAt > new Date()) {
        return {
          ...doc.result,
          isCached: true,
          cachedAt: doc.cachedAt.toISOString(),
        };
      }
    }
  } catch (err) {
    console.warn(`[CacheService] MongoDB read failed, checking in-memory cache: ${err.message}`);
  }

  // Fallback memory cache check
  if (memoryCache.has(hostPort)) {
    const cached = memoryCache.get(hostPort);
    if (cached.expiresAt > Date.now()) {
      return {
        ...cached.result,
        isCached: true,
        cachedAt: new Date(cached.cachedAt).toISOString(),
      };
    } else {
      memoryCache.delete(hostPort);
    }
  }

  return null;
}

/**
 * Upserts certificate result into cache
 */
async function setCachedCert(host, port, certResult, ttlSeconds = env.CACHE_TTL_SECONDS) {
  const hostPort = `${host.toLowerCase()}:${port}`;
  const now = new Date();
  const expiresAt = new Date(now.getTime() + ttlSeconds * 1000);

  // Always update fallback memory cache
  memoryCache.set(hostPort, {
    result: certResult,
    cachedAt: now.getTime(),
    expiresAt: expiresAt.getTime(),
  });

  try {
    await CertCache.findOneAndUpdate(
      { hostPort },
      {
        hostPort,
        host: host.toLowerCase(),
        port,
        result: certResult,
        cachedAt: now,
        expiresAt,
      },
      { upsert: true, new: true }
    );
  } catch (err) {
    console.warn(`[CacheService] MongoDB write failed: ${err.message}`);
  }
}

module.exports = { getCachedCert, setCachedCert };
