/**
 * Rate Limiter — Per-IP rate limiting using express-rate-limit with in-memory store.
 */

import rateLimit from 'express-rate-limit';
import { ENV } from '../config/env';

export const rateLimiter = rateLimit({
  windowMs: ENV.RATE_LIMIT_WINDOW_MS,
  max: ENV.RATE_LIMIT_MAX,
  standardHeaders: true,
  legacyHeaders: false,
  skipSuccessfulRequests: false,
  message: {
    error: true,
    message: 'Too many requests, please try again shortly.',
  },
  statusCode: 429,
});
