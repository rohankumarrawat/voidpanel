"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = require("express");
const dnsController_1 = require("../controllers/dnsController");
const validateDomain_1 = require("../middleware/validateDomain");
const rateLimiter_1 = require("../middleware/rateLimiter");
const router = (0, express_1.Router)();
/**
 * GET /api/tools/dns?domain=example.com&type=ALL|A|AAAA|…
 */
router.get('/', rateLimiter_1.rateLimiter, validateDomain_1.validateDomainMiddleware, dnsController_1.getDnsRecords);
exports.default = router;
//# sourceMappingURL=dns.js.map