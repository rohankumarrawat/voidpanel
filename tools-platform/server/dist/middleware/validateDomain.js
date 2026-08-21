"use strict";
/**
 * Domain Validation Middleware
 * Rejects requests before any DB or DoH call is made.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.validateDomainMiddleware = validateDomainMiddleware;
const VALID_TYPES = new Set([
    'ALL', 'A', 'AAAA', 'CNAME', 'MX', 'NS', 'TXT', 'SOA', 'CAA', 'SRV',
]);
const DOMAIN_REGEX = /^(?!-)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}$/;
const IPV4_REGEX = /^(\d{1,3}\.){3}\d{1,3}$/;
const IPV6_REGEX = /^[0-9a-fA-F:]+:[0-9a-fA-F:]*$/;
const BLOCKED_HOSTNAMES = new Set(['localhost', '127.0.0.1', '::1']);
function validateDomainMiddleware(req, res, next) {
    const rawDomain = req.query.domain;
    const rawType = req.query.type;
    if (!rawDomain || typeof rawDomain !== 'string' || rawDomain.trim() === '') {
        res.status(400).json({
            error: true,
            message: 'Missing required query parameter: domain.',
        });
        return;
    }
    const domain = rawDomain.trim().toLowerCase();
    if (BLOCKED_HOSTNAMES.has(domain)) {
        res.status(400).json({
            error: true,
            message: `"${domain}" is a reserved hostname and cannot be queried.`,
        });
        return;
    }
    if (IPV4_REGEX.test(domain) || IPV6_REGEX.test(domain)) {
        res.status(400).json({
            error: true,
            message: 'IP address literals are not supported. Please provide a domain name.',
        });
        return;
    }
    if (!DOMAIN_REGEX.test(domain)) {
        res.status(400).json({
            error: true,
            message: 'Invalid domain format. Please enter a fully qualified domain name.',
        });
        return;
    }
    if (rawType !== undefined) {
        if (typeof rawType !== 'string' || !VALID_TYPES.has(rawType.toUpperCase())) {
            res.status(400).json({
                error: true,
                message: `Invalid record type "${rawType}". Accepted: ${[...VALID_TYPES].join(', ')}.`,
            });
            return;
        }
    }
    next();
}
//# sourceMappingURL=validateDomain.js.map