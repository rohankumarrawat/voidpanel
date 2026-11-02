const mongoose = require('mongoose');

const rateLimitSchema = new mongoose.Schema(
  {
    ipHash: { type: String, required: true, index: true },
    count: { type: Number, default: 1 },
    expiresAt: { type: Date, required: true },
  },
  { timestamps: true }
);

rateLimitSchema.index({ expiresAt: 1 }, { expireAfterSeconds: 0 });
rateLimitSchema.index({ ipHash: 1, expiresAt: 1 });

module.exports = mongoose.model('RateLimit', rateLimitSchema);
