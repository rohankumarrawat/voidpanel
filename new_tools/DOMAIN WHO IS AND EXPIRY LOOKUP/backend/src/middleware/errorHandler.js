/**
 * Centralized Express Error Handler
 */
function errorHandler(err, req, res, next) {
  console.error(`[Express Error] ${err.stack || err.message}`);

  const statusCode = err.status || err.statusCode || 500;
  const message = err.message || 'An unexpected error occurred while processing the WHOIS lookup.';

  res.status(statusCode).json({
    success: false,
    error: message,
    timestamp: new Date().toISOString(),
  });
}

module.exports = errorHandler;
