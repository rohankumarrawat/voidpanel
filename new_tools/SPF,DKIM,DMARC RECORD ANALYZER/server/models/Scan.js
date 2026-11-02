import mongoose from 'mongoose';

const scanSchema = new mongoose.Schema(
  {
    domain: {
      type: String,
      required: true,
      index: true,
      lowercase: true,
      trim: true,
    },
    overallScore: {
      type: String,
      enum: ['Good', 'Needs Improvement', 'Poor'],
      required: true,
    },
    spf: {
      found: Boolean,
      record: String,
      valid: Boolean,
      lookupCount: Number,
      maxLookupsExceeded: Boolean,
      terminalQualifier: String,
      issues: [String],
      lookupTree: [mongoose.Schema.Types.Mixed],
    },
    dkim: {
      selectorsChecked: [String],
      foundCount: Number,
      results: [mongoose.Schema.Types.Mixed],
    },
    dmarc: {
      found: Boolean,
      record: String,
      policy: String,
      subdomainPolicy: String,
      pct: Number,
      rua: [String],
      ruf: [String],
      alignment: {
        spf: String,
        dkim: String,
      },
      issues: [String],
    },
    clientIp: {
      type: String,
      default: 'unknown',
    },
    timestamp: {
      type: Date,
      default: Date.now,
    },
  },
  {
    timestamps: true,
  }
);

export const Scan = mongoose.models.Scan || mongoose.model('Scan', scanSchema);
