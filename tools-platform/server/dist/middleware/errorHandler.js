"use strict";
/**
 * Centralized Error Handler
 * Must be registered as the LAST middleware in server.ts.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.errorHandler = errorHandler;
function errorHandler(err, req, res, _next) {
    console.error(`[Error] ${req.method} ${req.path}`, {
        message: err.message,
        stack: err.stack,
    });
    const statusCode = err.status ?? err.statusCode ?? 500;
    res.status(statusCode).json({
        error: true,
        message: statusCode >= 500
            ? 'An internal server error occurred.'
            : err.message ?? 'An unexpected error occurred.',
    });
}
//# sourceMappingURL=errorHandler.js.map