const crypto = require('crypto');

/**
 * Anonymizes client IP address using SHA-256 hash.
 */
function hashIp(ip) {
  const normalizedIp = (ip || '127.0.0.1').toString().trim();
  return crypto.createHash('sha256').update(normalizedIp + '_voidonyx_salt').digest('hex');
}

/**
 * Extracts client IP from Express request headers or socket.
 */
function getClientIp(req) {
  const forwarded = req.headers['x-forwarded-for'];
  if (forwarded) {
    return forwarded.split(',')[0].trim();
  }
  return req.ip || req.connection?.remoteAddress || '127.0.0.1';
}

module.exports = { hashIp, getClientIp };
