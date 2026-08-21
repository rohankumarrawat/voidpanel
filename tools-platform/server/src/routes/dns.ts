import { Router } from 'express';
import { getDnsRecords } from '../controllers/dnsController';
import { validateDomainMiddleware } from '../middleware/validateDomain';
import { rateLimiter } from '../middleware/rateLimiter';

const router = Router();

/**
 * GET /api/tools/dns?domain=example.com&type=ALL|A|AAAA|…
 */
router.get('/', rateLimiter, validateDomainMiddleware, getDnsRecords);

export default router;
