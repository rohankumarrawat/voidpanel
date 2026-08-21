import { Request, Response, NextFunction } from 'express';
/**
 * GET /api/tools/dns?domain=example.com&type=ALL|A|AAAA|…
 */
export declare function getDnsRecords(req: Request, res: Response, next: NextFunction): Promise<void>;
//# sourceMappingURL=dnsController.d.ts.map