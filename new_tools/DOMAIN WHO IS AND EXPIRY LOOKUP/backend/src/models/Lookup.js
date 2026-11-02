const mongoose = require('mongoose');

const lookupSchema = new mongoose.Schema(
  {
    domain: { type: String, required: true, index: true },
    tld: { type: String, required: true, index: true },
    source: { type: String, enum: ['rdap', 'whois', 'cache'], required: true },
    status: {
      type: String,
      enum: ['active', 'expiring', 'expired', 'available', 'error', 'privacy_protected'],
      required: true,
    },
    daysRemaining: { type: Number, default: null },
    registrar: {
      name: { type: String, default: null },
      ianaId: { type: String, default: null },
      url: { type: String, default: null },
      email: { type: String, default: null },
    },
    createdDate: { type: Date, default: null },
    expiresDate: { type: Date, default: null },
    updatedDate: { type: Date, default: null },
    nameServers: [{ type: String }],
    statusFlags: [{ type: String }],
    parsedStatusDetails: [
      {
        code: { type: String },
        description: { type: String },
      },
    ],
    dnssec: { type: String, enum: ['signed', 'unsigned', 'unknown'], default: 'unknown' },
    privacyProtected: { type: Boolean, default: false },
    registrantOrg: { type: String, default: null },
    checkedAt: { type: Date, default: Date.now, index: true },
    requesterIpHash: { type: String, required: true, index: true },
    sessionId: { type: String, default: null, index: true },
  },
  { timestamps: true }
);

lookupSchema.index({ domain: 1, checkedAt: -1 });
lookupSchema.index({ sessionId: 1, checkedAt: -1 });

module.exports = mongoose.model('Lookup', lookupSchema);
