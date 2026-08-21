/**
 * Domain Validation Middleware
 * Rejects requests before any DB or DoH call is made.
 */
import { Request, Response, NextFunction } from 'express';
export declare function validateDomainMiddleware(req: Request, res: Response, next: NextFunction): void;
//# sourceMappingURL=validateDomain.d.ts.map