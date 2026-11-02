const mongoose = require('mongoose');
const path = require('path');
require('dotenv').config({ path: path.resolve(__dirname, '../.env') });

const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017/ssl_checker';

// Inline Mongoose Schema Definitions for standalone execution
const LookupSchema = new mongoose.Schema({
  host: String,
  port: Number,
  status: String,
  daysRemaining: Number,
  issuer: Object,
  subject: Object,
  sans: [String],
  notBefore: Date,
  notAfter: Date,
  fingerprintSha256: String,
  tlsVersionsSupported: [String],
  checkedAt: { type: Date, default: Date.now },
  requesterIpHash: String,
});
LookupSchema.index({ host: 1, port: 1 });
LookupSchema.index({ checkedAt: -1 });

const CertCacheSchema = new mongoose.Schema({
  hostPort: { type: String, unique: true },
  host: String,
  port: Number,
  result: Object,
  cachedAt: { type: Date, default: Date.now },
  expiresAt: Date,
});
CertCacheSchema.index({ expiresAt: 1 }, { expireAfterSeconds: 0 });

const RateLimitSchema = new mongoose.Schema({
  ipHash: { type: String, unique: true },
  count: Number,
  windowStart: Date,
  expiresAt: Date,
});
RateLimitSchema.index({ expiresAt: 1 }, { expireAfterSeconds: 0 });

const Lookup = mongoose.model('Lookup', LookupSchema);
const CertCache = mongoose.model('CertCache', CertCacheSchema);
const RateLimit = mongoose.model('RateLimit', RateLimitSchema);

async function seed() {
  console.log(`Connecting to MongoDB at ${MONGODB_URI}...`);
  try {
    await mongoose.connect(MONGODB_URI);
    console.log('✅ Connected to MongoDB.');

    console.log('Ensuring indexes are created...');
    await Lookup.createIndexes();
    await CertCache.createIndexes();
    await RateLimit.createIndexes();
    console.log('✅ Indexes verified/created.');

    console.log('Seeding sample lookup records...');
    await Lookup.deleteMany({});

    const dummyIpHash = 'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3';

    const sampleLookups = [
      {
        host: 'google.com',
        port: 443,
        status: 'valid',
        daysRemaining: 68,
        issuer: { cn: 'GTS CA 1C3', o: 'Google Trust Services LLC' },
        subject: { cn: '*.google.com', o: 'Google LLC' },
        sans: ['*.google.com', 'google.com', '*.youtube.com'],
        notBefore: new Date(Date.now() - 86400000 * 22),
        notAfter: new Date(Date.now() + 86400000 * 68),
        fingerprintSha256: '9A:43:2F:E1:5D:89:0A:78:22:90:BA:CD:EF:12:34:56:78:90:AB:CD:EF:12:34:56:78:90:AB:CD:EF:12:34:56',
        tlsVersionsSupported: ['TLSv1.3', 'TLSv1.2'],
        checkedAt: new Date(Date.now() - 600000),
        requesterIpHash: dummyIpHash,
      },
      {
        host: 'expired.badssl.com',
        port: 443,
        status: 'expired',
        daysRemaining: -1640,
        issuer: { cn: 'COMODO RSA Domain Validation Secure Server CA', o: 'COMODO CA Limited' },
        subject: { cn: '*.badssl.com' },
        sans: ['*.badssl.com', 'badssl.com'],
        notBefore: new Date('2015-04-09T00:00:00Z'),
        notAfter: new Date('2018-04-12T23:59:59Z'),
        fingerprintSha256: 'C5:A0:82:13:B9:4C:E6:D3:5F:2A:78:91:02:43:87:65:09:BA:DC:FE:21:43:65:87:09:BA:DC:FE:21:43:65:87',
        tlsVersionsSupported: ['TLSv1.2'],
        checkedAt: new Date(Date.now() - 300000),
        requesterIpHash: dummyIpHash,
      },
      {
        host: 'self-signed.badssl.com',
        port: 443,
        status: 'untrusted',
        daysRemaining: 180,
        issuer: { cn: '*.badssl.com' },
        subject: { cn: '*.badssl.com' },
        sans: ['*.badssl.com', 'badssl.com'],
        notBefore: new Date(Date.now() - 86400000 * 180),
        notAfter: new Date(Date.now() + 86400000 * 180),
        fingerprintSha256: '12:34:56:78:90:AB:CD:EF:12:34:56:78:90:AB:CD:EF:12:34:56:78:90:AB:CD:EF:12:34:56:78:90:AB:CD:EF',
        tlsVersionsSupported: ['TLSv1.2'],
        checkedAt: new Date(Date.now() - 120000),
        requesterIpHash: dummyIpHash,
      },
      {
        host: 'voidonyx.in',
        port: 443,
        status: 'valid',
        daysRemaining: 42,
        issuer: { cn: 'E1', o: 'Let\'s Encrypt' },
        subject: { cn: 'voidonyx.in' },
        sans: ['voidonyx.in', '*.voidonyx.in', 'tools.voidonyx.in'],
        notBefore: new Date(Date.now() - 86400000 * 48),
        notAfter: new Date(Date.now() + 86400000 * 42),
        fingerprintSha256: '00:FF:66:AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66',
        tlsVersionsSupported: ['TLSv1.3', 'TLSv1.2'],
        checkedAt: new Date(),
        requesterIpHash: dummyIpHash,
      },
    ];

    await Lookup.insertMany(sampleLookups);
    console.log(`✅ Seeded ${sampleLookups.length} sample lookup audit records.`);

    await mongoose.disconnect();
    console.log('Seed completed successfully.');
    process.exit(0);
  } catch (err) {
    console.error('❌ Seeding failed:', err.message);
    process.exit(1);
  }
}

seed();
