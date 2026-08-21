"use strict";
/**
 * DoH Resolver Service
 * Performs DNS-over-HTTPS lookups using:
 *   Primary:  Cloudflare → https://cloudflare-dns.com/dns-query
 *   Fallback: Google     → https://dns.google/resolve
 */
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.resolveRecords = resolveRecords;
const axios_1 = __importDefault(require("axios"));
const DOH_CLOUDFLARE = 'https://cloudflare-dns.com/dns-query';
const DOH_GOOGLE = 'https://dns.google/resolve';
const TIMEOUT_MS = 5000;
const ALL_RECORD_TYPES = [
    'A', 'AAAA', 'CNAME', 'MX', 'NS', 'TXT', 'SOA', 'CAA', 'SRV',
];
const TYPE_TO_NUM = {
    A: 1, NS: 2, CNAME: 5, SOA: 6, MX: 15, TXT: 16, AAAA: 28, SRV: 33, CAA: 257,
};
const NUM_TO_TYPE = Object.fromEntries(Object.entries(TYPE_TO_NUM).map(([k, v]) => [v, k]));
async function queryEndpoint(url, domain, type) {
    const response = await axios_1.default.get(url, {
        params: { name: domain, type },
        headers: { Accept: 'application/dns-json' },
        timeout: TIMEOUT_MS,
    });
    return response.data;
}
async function resolveType(domain, type) {
    let data;
    try {
        data = await queryEndpoint(DOH_CLOUDFLARE, domain, type);
    }
    catch {
        try {
            data = await queryEndpoint(DOH_GOOGLE, domain, type);
        }
        catch (fallbackErr) {
            const isTimeout = axios_1.default.isAxiosError(fallbackErr) &&
                fallbackErr.code === 'ECONNABORTED';
            return [
                {
                    type,
                    host: domain,
                    value: '',
                    ttl: 0,
                    status: 'error',
                    error: isTimeout
                        ? 'DNS query timed out on both Cloudflare and Google DoH'
                        : 'Failed to reach Cloudflare and Google DoH providers',
                },
            ];
        }
    }
    if (!data.Answer || data.Answer.length === 0) {
        return [{ type, host: domain, value: '', ttl: 0, status: 'not_found' }];
    }
    return data.Answer.map((answer) => ({
        type: NUM_TO_TYPE[answer.type] ?? type,
        host: answer.name.replace(/\.$/, ''),
        value: answer.data.replace(/\.$/, ''),
        ttl: answer.TTL,
        status: 'found',
    }));
}
async function resolveRecords(domain, type) {
    const types = type === 'ALL' ? ALL_RECORD_TYPES : [type];
    const settled = await Promise.allSettled(types.map((t) => resolveType(domain, t)));
    const records = [];
    for (const result of settled) {
        if (result.status === 'fulfilled') {
            records.push(...result.value);
        }
        else {
            records.push({
                type: 'UNKNOWN',
                host: domain,
                value: '',
                ttl: 0,
                status: 'error',
                error: String(result.reason),
            });
        }
    }
    const allNotFound = records.every((r) => r.status === 'not_found');
    const isNxdomain = type === 'ALL' && allNotFound;
    return { records, isNxdomain };
}
//# sourceMappingURL=dohResolver.js.map