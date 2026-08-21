import dotenv from 'dotenv';
dotenv.config();

function requireEnv(key: string, fallback?: string): string {
  const val = process.env[key] ?? fallback;
  if (val === undefined) {
    throw new Error(`Missing required environment variable: ${key}`);
  }
  return val;
}

export const ENV = {
  PORT: parseInt(process.env.PORT ?? '3002', 10),
  NODE_ENV: process.env.NODE_ENV ?? 'development',
  MONGODB_URI: requireEnv('MONGO_URI', 'mongodb://localhost:27017/voidtools_db'),
  CACHE_TTL_SECONDS: parseInt(process.env.CACHE_TTL_SECONDS ?? '300', 10),
  RATE_LIMIT_MAX: parseInt(process.env.RATE_LIMIT_MAX ?? '30', 10),
  RATE_LIMIT_WINDOW_MS: parseInt(process.env.RATE_LIMIT_WINDOW_MS ?? '60000', 10),
  CORS_ORIGIN: process.env.CORS_ORIGIN ?? 'https://tools.voidonyx.in',
  IP_SALT: process.env.IP_SALT ?? 'voidtools-dns-salt',
} as const;
