"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.DnsCache = void 0;
const mongoose_1 = __importStar(require("mongoose"));
const env_1 = require("../config/env");
const DnsCacheSchema = new mongoose_1.Schema({
    domain: { type: String, required: true },
    type: { type: String, required: true },
    records: { type: mongoose_1.Schema.Types.Mixed, required: true },
    queryTimeMs: { type: Number, required: true },
    createdAt: { type: Date, default: Date.now, expires: env_1.ENV.CACHE_TTL_SECONDS },
}, { versionKey: false });
DnsCacheSchema.index({ domain: 1, type: 1 }, { unique: true });
exports.DnsCache = mongoose_1.default.model('DnsCache', DnsCacheSchema);
//# sourceMappingURL=DnsCache.js.map