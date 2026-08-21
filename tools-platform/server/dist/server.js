"use strict";
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
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const cors_1 = __importDefault(require("cors"));
const helmet_1 = __importDefault(require("helmet"));
const morgan_1 = __importDefault(require("morgan"));
const env_1 = require("./config/env");
const db_1 = require("./config/db");
const errorHandler_1 = require("./middleware/errorHandler");
const dns_1 = __importDefault(require("./routes/dns"));
const history_1 = __importDefault(require("./routes/history"));
const health_1 = __importDefault(require("./routes/health"));
const registry_1 = __importDefault(require("./routes/registry"));
const app = (0, express_1.default)();
// ── Trust proxy headers (needed to get real IP behind Nginx/Cloudflare) ──
app.set('trust proxy', 1);
// ── Security headers ──────────────────────────────────────────────────────
app.use((0, helmet_1.default)());
// ── CORS — restricted to the configured frontend origin ───────────────────
app.use((0, cors_1.default)({
    origin: env_1.ENV.CORS_ORIGIN,
    methods: ['GET', 'OPTIONS'],
    allowedHeaders: ['Content-Type'],
    optionsSuccessStatus: 200,
}));
// ── Request logging ───────────────────────────────────────────────────────
app.use((0, morgan_1.default)(env_1.ENV.NODE_ENV === 'production' ? 'combined' : 'dev'));
// ── Body parsing with tight size limit ────────────────────────────────────
app.use(express_1.default.json({ limit: '10kb' }));
// ── API routes ────────────────────────────────────────────────────────────
app.use('/api/tools/dns', dns_1.default); // DNS Checker
app.use('/api/tools/registry', registry_1.default); // Tool registry
app.use('/api/history', history_1.default); // Query history
app.use('/api/health', health_1.default); // Health check
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
app.use(errorHandler_1.errorHandler);
// ── Bootstrap ─────────────────────────────────────────────────────────────
async function start() {
    await (0, db_1.connectDB)();
    app.listen(env_1.ENV.PORT, '127.0.0.1', () => {
        console.log(`[Server] VoidOnyx Tools API running on http://127.0.0.1:${env_1.ENV.PORT} [${env_1.ENV.NODE_ENV}]`);
        console.log(`[Server] CORS origin: ${env_1.ENV.CORS_ORIGIN}`);
    });
}
start().catch((err) => {
    console.error('[Server] Fatal startup error:', err);
    process.exit(1);
});
//# sourceMappingURL=server.js.map