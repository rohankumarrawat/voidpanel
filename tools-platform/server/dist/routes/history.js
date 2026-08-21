"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = require("express");
const historyController_1 = require("../controllers/historyController");
const router = (0, express_1.Router)();
router.get('/recent', historyController_1.getRecentHistory);
exports.default = router;
//# sourceMappingURL=history.js.map