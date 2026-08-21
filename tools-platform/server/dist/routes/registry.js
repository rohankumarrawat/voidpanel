"use strict";
/**
 * VoidOnyx Tool Registry
 * ======================
 * Central registry of all available tools on the platform.
 * Adding a new tool = adding one entry here + creating the tool folder in client/src/tools/
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.TOOLS_REGISTRY = void 0;
const express_1 = require("express");
exports.TOOLS_REGISTRY = [
    {
        slug: 'dns-checker',
        name: 'DNS Record Checker',
        description: 'Lookup A, MX, TXT, CNAME, NS, and more DNS records for any domain via DoH.',
        category: 'DNS & Domain',
        icon: '🌐',
        status: 'live',
        path: '/tools/dns-checker',
        apiPrefix: '/api/tools/dns',
    },
    {
        slug: 'whois-lookup',
        name: 'WHOIS Lookup',
        description: 'Get registration details, nameservers, and expiry date for any domain.',
        category: 'DNS & Domain',
        icon: '🔍',
        status: 'coming-soon',
        path: '/tools/whois-lookup',
    },
    {
        slug: 'ip-lookup',
        name: 'IP Geolocation',
        description: 'Find the geographic location, ISP, and ASN info for any IP address.',
        category: 'Networking',
        icon: '📍',
        status: 'coming-soon',
        path: '/tools/ip-lookup',
    },
    {
        slug: 'ssl-checker',
        name: 'SSL Certificate Checker',
        description: 'Verify SSL/TLS certificates, expiry dates, chain validity, and cipher strength.',
        category: 'SSL & Security',
        icon: '🔒',
        status: 'coming-soon',
        path: '/tools/ssl-checker',
    },
    {
        slug: 'mx-lookup',
        name: 'MX Record Lookup',
        description: 'Check mail exchange records, priorities, and email deliverability for a domain.',
        category: 'Email',
        icon: '📧',
        status: 'coming-soon',
        path: '/tools/mx-lookup',
    },
    {
        slug: 'spf-validator',
        name: 'SPF Record Validator',
        description: 'Validate SPF records and check DNS-based sender authorization for email.',
        category: 'Email',
        icon: '🛡️',
        status: 'coming-soon',
        path: '/tools/spf-validator',
    },
    {
        slug: 'http-headers',
        name: 'HTTP Header Inspector',
        description: 'Inspect HTTP response headers, security headers, and server configuration.',
        category: 'SSL & Security',
        icon: '🔬',
        status: 'coming-soon',
        path: '/tools/http-headers',
    },
    {
        slug: 'utm-builder',
        name: 'UTM Link Builder',
        description: 'Generate UTM-tagged campaign URLs for Google Analytics tracking.',
        category: 'Marketing',
        icon: '🔗',
        status: 'coming-soon',
        path: '/tools/utm-builder',
    },
];
const router = (0, express_1.Router)();
/**
 * GET /api/tools/registry — Returns all tools with their metadata
 * Optional query: ?status=live to filter by status
 */
router.get('/', (req, res) => {
    const statusFilter = req.query.status;
    let tools = exports.TOOLS_REGISTRY;
    if (statusFilter) {
        tools = tools.filter((t) => t.status === statusFilter);
    }
    res.json({
        count: tools.length,
        tools,
    });
});
exports.default = router;
//# sourceMappingURL=registry.js.map