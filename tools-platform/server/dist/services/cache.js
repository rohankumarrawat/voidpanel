"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.getCachedResult = getCachedResult;
exports.setCachedResult = setCachedResult;
const DnsCache_1 = require("../models/DnsCache");
async function getCachedResult(domain, type) {
    try {
        return await DnsCache_1.DnsCache.findOne({ domain, type }).lean();
    }
    catch {
        return null;
    }
}
async function setCachedResult(domain, type, records, queryTimeMs) {
    try {
        await DnsCache_1.DnsCache.findOneAndUpdate({ domain, type }, { domain, type, records, queryTimeMs, createdAt: new Date() }, { upsert: true, new: true });
    }
    catch (err) {
        console.warn('[Cache] Write failed (non-fatal):', err.message);
    }
}
//# sourceMappingURL=cache.js.map