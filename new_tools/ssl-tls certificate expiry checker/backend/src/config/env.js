const path = require('path');
require('dotenv').config({ path: path.resolve(__dirname, '../../.env') });

module.exports = {
  PORT: process.env.PORT || 5000,
  MONGODB_URI: process.env.MONGODB_URI || 'mongodb://localhost:27017/ssl_checker',
  CACHE_TTL_SECONDS: parseInt(process.env.CACHE_TTL_SECONDS || '600', 10), // 10 mins
  RATE_LIMIT_WINDOW_SECONDS: parseInt(process.env.RATE_LIMIT_WINDOW_SECONDS || '60', 10), // 1 min
  RATE_LIMIT_MAX_REQUESTS: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS || '10', 10), // 10 req/min
  TLS_TIMEOUT_MS: parseInt(process.env.TLS_TIMEOUT_MS || '8000', 10), // 8 seconds
  NODE_ENV: process.env.NODE_ENV || 'development'
};
