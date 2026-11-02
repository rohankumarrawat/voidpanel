import rateLimit from 'express-rate-limit';

export const analyzeRateLimiter = rateLimit({
  windowMs: Number(process.env.RATE_LIMIT_WINDOW_MS || 60000), // 1 minute window
  max: Number(process.env.RATE_LIMIT_MAX || 20), // limit each IP to 20 requests per window
  standardHeaders: true,
  legacyHeaders: false,
  message: {
    error: 'Too many analysis requests from this IP address. Please try again after 60 seconds.',
    kind: 'rate_limit',
  },
});
