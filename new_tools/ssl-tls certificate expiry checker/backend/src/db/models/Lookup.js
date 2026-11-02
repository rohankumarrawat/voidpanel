const mongoose = require('mongoose');

const LookupSchema = new mongoose.Schema({
  host: {
    type: String,
    required: true,
    trim: true,
    lowercase: true,
    index: true,
  },
  port: {
    type: Number,
    required: true,
    default: 443,
  },
  status: {
    type: String,
    required: true,
    enum: ['valid', 'expiring', 'expired', 'untrusted', 'error'],
  },
  daysRemaining: {
    type: Number,
    default: null,
  },
  issuer: {
    type: mongoose.Schema.Types.Mixed,
  },
  subject: {
    type: mongoose.Schema.Types.Mixed,
  },
  sans: [{
    type: String,
  }],
  notBefore: Date,
  notAfter: Date,
  fingerprintSha256: String,
  tlsVersionsSupported: [{
    type: String,
  }],
  checkedAt: {
    type: Date,
    default: Date.now,
    index: true,
  },
  requesterIpHash: {
    type: String,
    required: true,
    index: true,
  },
});

LookupSchema.index({ host: 1, port: 1 });
LookupSchema.index({ checkedAt: -1 });

module.exports = mongoose.model('Lookup', LookupSchema);

