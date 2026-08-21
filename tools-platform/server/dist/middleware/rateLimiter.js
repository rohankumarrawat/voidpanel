"use strict";
/**
 * Rate Limiter — Per-IP rate limiting using express-rate-limit with in-memory store.
 */
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.rateLimiter = void 0;
const express_rate_limit_1 = __importDefault(require("express-rate-limit"));
const env_1 = require("../config/env");
exports.rateLimiter = (0, express_rate_limit_1.default)({
    windowMs: env_1.ENV.RATE_LIMIT_WINDOW_MS,
    max: env_1.ENV.RATE_LIMIT_MAX,
    standardHeaders: true,
    legacyHeaders: false,
    skipSuccessfulRequests: false,
    message: {
        error: true,
        message: 'Too many requests, please try again shortly.',
    },
    statusCode: 429,
});
//# sourceMappingURL=rateLimiter.js.map