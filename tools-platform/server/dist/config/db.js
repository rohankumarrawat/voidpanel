"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.connectDB = connectDB;
const mongoose_1 = __importDefault(require("mongoose"));
const env_1 = require("./env");
async function connectDB() {
    try {
        mongoose_1.default.set('strictQuery', true);
        await mongoose_1.default.connect(env_1.ENV.MONGODB_URI, { serverSelectionTimeoutMS: 5000 });
        console.log(`[DB] MongoDB connected → ${env_1.ENV.MONGODB_URI.replace(/\/\/.*@/, '//<credentials>@')}`);
    }
    catch (err) {
        console.warn('[DB] MongoDB unavailable — running without caching/history.');
        console.warn('[DB] Error:', err.message);
        // Don't crash — tools work without DB, just without caching
    }
}
// Gracefully close on process exit
process.on('SIGINT', async () => {
    await mongoose_1.default.connection.close();
    console.log('[DB] Connection closed on SIGINT');
    process.exit(0);
});
//# sourceMappingURL=db.js.map