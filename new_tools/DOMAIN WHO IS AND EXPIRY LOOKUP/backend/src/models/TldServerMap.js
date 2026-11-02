const mongoose = require('mongoose');

const tldServerMapSchema = new mongoose.Schema(
  {
    tld: { type: String, required: true, unique: true, index: true },
    rdapUrls: [{ type: String }],
    whoisServer: { type: String, default: null },
    lastFetchedAt: { type: Date, default: Date.now },
  },
  { timestamps: true }
);

module.exports = mongoose.model('TldServerMap', tldServerMapSchema);
