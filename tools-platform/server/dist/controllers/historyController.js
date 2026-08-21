"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.getRecentHistory = getRecentHistory;
const LookupHistory_1 = require("../models/LookupHistory");
async function getRecentHistory(req, res) {
    try {
        const limit = Math.min(parseInt(req.query.limit) || 20, 100);
        const recent = await LookupHistory_1.LookupHistory.find()
            .sort({ timestamp: -1 })
            .limit(limit)
            .select('-ipHash')
            .lean();
        res.json({ history: recent });
    }
    catch (err) {
        res.status(500).json({ error: true, message: 'Failed to fetch history.' });
    }
}
//# sourceMappingURL=historyController.js.map