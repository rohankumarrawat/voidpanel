const mongoose = require('mongoose');

const CertCacheSchema = new mongoose.Schema({
  hostPort: {
    type: String,
    required: true,
    unique: true,
    index: true,
  },
  host: {
    type: String,
    required: true,
    lowercase: true,
  },
  port: {
    type: Number,
    required: true,
  },
  result: {
    type: mongoose.Schema.Types.Mixed,
    required: true,
  },
  cachedAt: {
    type: Date,
    default: Date.now,
  },
  expiresAt: {
    type: Date,
    required: true,
  },
});

// Create MongoDB TTL index so documents auto-expire when expiresAt is reached
CertCacheSchema.index({ expiresAt: 1 }, { expireAfterSeconds: 0 });

module.exports = mongoose.model('CertCache', CertCacheSchema);
