const mongoose = require('mongoose');

const whoisCacheSchema = new mongoose.Schema(
  {
    domain: { type: String, required: true, unique: true, index: true },
    tld: { type: String, required: true },
    data: { type: Object, required: true },
    expiresAt: { type: Date, required: true },
  },
  { timestamps: true }
);

// TTL index to automatically drop expired cache documents
whoisCacheSchema.index({ expiresAt: 1 }, { expireAfterSeconds: 0 });
whoisCacheSchema.index({ domain: 1, expiresAt: 1 });

module.exports = mongoose.model('WhoisCache', whoisCacheSchema);
