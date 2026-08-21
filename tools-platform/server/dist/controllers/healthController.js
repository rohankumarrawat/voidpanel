"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.getHealthStatus = getHealthStatus;
const mongoose_1 = __importDefault(require("mongoose"));
const os_1 = __importDefault(require("os"));
function getHealthStatus(_req, res) {
    const dbState = mongoose_1.default.connection.readyState;
    const dbStatus = dbState === 1 ? 'connected' : dbState === 2 ? 'connecting' : 'disconnected';
    res.json({
        status: 'ok',
        uptime: process.uptime(),
        timestamp: new Date().toISOString(),
        database: dbStatus,
        memory: {
            rss: Math.round(process.memoryUsage().rss / 1024 / 1024) + ' MB',
            heap: Math.round(process.memoryUsage().heapUsed / 1024 / 1024) + ' MB',
        },
        hostname: os_1.default.hostname(),
    });
}
//# sourceMappingURL=healthController.js.map