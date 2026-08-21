/**
 * VoidOnyx Tools Platform — Backend Entry Point
 * ===============================================
 * Express application serving all VoidOnyx free tools:
 *  - DNS Checker (DoH resolution via Cloudflare/Google)
 *  - Tool registry API
 *  - Health check endpoint
 *
 * Bootstrapped with Helmet, CORS, Morgan, rate limiting, and MongoDB.
 * Runs on PORT defined in .env (default 4100).
 */

import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';

import { ENV } from './config/env';
import { connectDB } from './config/db';
import { errorHandler } from './middleware/errorHandler';

import dnsRouter from './routes/dns';
import historyRouter from './routes/history';
import healthRouter from './routes/health';
import registryRouter from './routes/registry';

const app = express();

// ── Trust proxy headers (needed to get real IP behind Nginx/Cloudflare) ──
app.set('trust proxy', 1);

// ── Security headers ──────────────────────────────────────────────────────
app.use(helmet());

// ── CORS — restricted to the configured frontend origin ───────────────────
app.use(
  cors({
    origin: ENV.CORS_ORIGIN,
    methods: ['GET', 'OPTIONS'],
    allowedHeaders: ['Content-Type'],
    optionsSuccessStatus: 200,
  })
);

// ── Request logging ───────────────────────────────────────────────────────
app.use(morgan(ENV.NODE_ENV === 'production' ? 'combined' : 'dev'));

// ── Body parsing with tight size limit ────────────────────────────────────
app.use(express.json({ limit: '10kb' }));

// ── API routes ────────────────────────────────────────────────────────────
app.use('/api/tools/dns', dnsRouter);           // DNS Checker
app.use('/api/tools/registry', registryRouter); // Tool registry
app.use('/api/history', historyRouter);          // Query history
app.use('/api/health', healthRouter);            // Health check

// ── Root API info ─────────────────────────────────────────────────────────
app.get('/api', (_req, res) => {
  res.json({
    name: 'VoidOnyx Tools Platform API',
    version: '1.0.0',
    endpoints: [
      'GET /api/tools/dns?domain=example.com&type=ALL',
      'GET /api/tools/registry',
      'GET /api/health',
      'GET /api/history/recent',
    ],
  });
});

// ── 404 catch-all ────────────────────────────────────────────────────────
app.use((_req, res) => {
  res.status(404).json({ error: true, message: 'Endpoint not found.' });
});

// ── Centralised error handler (must be last) ──────────────────────────────
app.use(errorHandler);

// ── Bootstrap ─────────────────────────────────────────────────────────────
async function start(): Promise<void> {
  await connectDB();
  app.listen(ENV.PORT, '127.0.0.1', () => {
    console.log(
      `[Server] VoidOnyx Tools API running on http://127.0.0.1:${ENV.PORT} [${ENV.NODE_ENV}]`
    );
    console.log(`[Server] CORS origin: ${ENV.CORS_ORIGIN}`);
  });
}

start().catch((err) => {
  console.error('[Server] Fatal startup error:', err);
  process.exit(1);
});
