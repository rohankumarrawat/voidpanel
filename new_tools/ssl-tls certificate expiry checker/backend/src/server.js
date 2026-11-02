const app = require('./app');
const env = require('./config/env');
const { connectDB } = require('./db/connection');

async function startServer() {
  console.log('🔒 Starting VoidOnyX SSL/TLS Certificate Checker Service...');
  
  // Connect to MongoDB
  await connectDB();

  const server = app.listen(env.PORT, () => {
    console.log(`🚀 Server listening on http://localhost:${env.PORT}`);
    console.log(`   Environment: ${env.NODE_ENV}`);
    console.log(`   Cache TTL: ${env.CACHE_TTL_SECONDS}s`);
    console.log(`   Rate Limit: ${env.RATE_LIMIT_MAX_REQUESTS} req / ${env.RATE_LIMIT_WINDOW_SECONDS}s`);
  });

  const handleShutdown = async (signal) => {
    console.log(`\nReceived ${signal}. Shutting down gracefully...`);
    server.close(async () => {
      console.log('HTTP server closed.');
      process.exit(0);
    });
  };

  process.on('SIGINT', () => handleShutdown('SIGINT'));
  process.on('SIGTERM', () => handleShutdown('SIGTERM'));
}

startServer();
