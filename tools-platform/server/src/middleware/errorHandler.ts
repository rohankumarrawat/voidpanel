/**
 * Centralized Error Handler
 * Must be registered as the LAST middleware in server.ts.
 */

import { Request, Response, NextFunction } from 'express';

interface AppError extends Error {
  status?: number;
  statusCode?: number;
}

export function errorHandler(
  err: AppError,
  req: Request,
  res: Response,
  _next: NextFunction
): void {
  console.error(`[Error] ${req.method} ${req.path}`, {
    message: err.message,
    stack: err.stack,
  });

  const statusCode = err.status ?? err.statusCode ?? 500;

  res.status(statusCode).json({
    error: true,
    message:
      statusCode >= 500
        ? 'An internal server error occurred.'
        : err.message ?? 'An unexpected error occurred.',
  });
}
