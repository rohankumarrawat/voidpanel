/**
 * Centralized Error Handler
 * Must be registered as the LAST middleware in server.ts.
 */
import { Request, Response, NextFunction } from 'express';
interface AppError extends Error {
    status?: number;
    statusCode?: number;
}
export declare function errorHandler(err: AppError, req: Request, res: Response, _next: NextFunction): void;
export {};
//# sourceMappingURL=errorHandler.d.ts.map