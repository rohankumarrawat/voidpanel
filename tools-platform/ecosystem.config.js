module.exports = {
  apps: [{
    name: "voidtools",
    script: "dist/server.js",
    cwd: "/home/voidonyx/tools-platform/server",
    env: {
      NODE_ENV: "production",
      PORT: 4100,
      MONGO_URI: "mongodb://localhost:27017/voidtools_db",
      CORS_ORIGIN: "https://tools.voidonyx.in",
      CACHE_TTL_SECONDS: 300,
      RATE_LIMIT_MAX: 30,
      RATE_LIMIT_WINDOW_MS: 60000,
      IP_SALT: "voidtools-production-salt-change-me"
    }
  }]
};
