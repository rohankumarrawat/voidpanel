"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.getDnsRecords = getDnsRecords;
const crypto_1 = __importDefault(require("crypto"));
const dohResolver_1 = require("../services/dohResolver");
const cache_1 = require("../services/cache");
const LookupHistory_1 = require("../models/LookupHistory");
const env_1 = require("../config/env");
function hashIP(ip) {
    return crypto_1.default
        .createHash('sha256')
        .update(ip + env_1.ENV.IP_SALT)
        .digest('hex');
}
/**
 * GET /api/tools/dns?domain=example.com&type=ALL|A|AAAA|…
 */
async function getDnsRecords(req, res, next) {
    try {
        const domain = req.query.domain.trim().toLowerCase();
        const type = (req.query.type ?? 'ALL').toUpperCase();
        // 1. Cache check
        const cached = await (0, cache_1.getCachedResult)(domain, type);
        if (cached) {
            res.json({
                domain,
                type,
                records: cached.records,
                cached: true,
                queryTimeMs: cached.queryTimeMs,
                isNxdomain: false,
            });
            return;
        }
        // 2. Live DoH resolution
        const startMs = Date.now();
        const { records, isNxdomain } = await (0, dohResolver_1.resolveRecords)(domain, type);
        const queryTimeMs = Date.now() - startMs;
        // 3. Determine overall status
        const hasFound = records.some((r) => r.status === 'found');
        const hasError = records.some((r) => r.status === 'error');
        const overallStatus = hasFound
            ? 'success'
            : hasError
                ? 'error'
                : 'not_found';
        // 4. Persist to cache (non-blocking)
        void (0, cache_1.setCachedResult)(domain, type, records, queryTimeMs);
        // 5. Write history entry
        const rawIP = req.headers['x-forwarded-for']?.split(',')[0]?.trim() ??
            req.ip ??
            req.socket.remoteAddress ??
            'unknown';
        void LookupHistory_1.LookupHistory.create({
            domain,
            type,
            status: overallStatus,
            timestamp: new Date(),
            ipHash: hashIP(rawIP),
        }).catch((err) => {
            console.warn('[History] Write failed (non-fatal):', err.message);
        });
        // 6. Respond
        res.json({ domain, type, records, cached: false, queryTimeMs, isNxdomain });
    }
    catch (err) {
        next(err);
    }
}
//# sourceMappingURL=dnsController.js.map