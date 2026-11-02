const mongoose = require('mongoose');

const RateLimitSchema = new mongoose.Schema({
  ipHash: {
    type: String,
    required: true,
    unique: true,
    index: true,
  },
  count: {
    type: Number,
    required: true,
    default: 1,
  },
  windowStart: {
    type: Date,
    default: Date.now,
  },
  expiresAt: {
    type: Date,
    required: true,
  },
});

RateLimitSchema.index({ expiresAt: 1 }, { expireAfterSeconds: 0 });

module.exports = mongoose.model('RateLimit', RateLimitSchema);
