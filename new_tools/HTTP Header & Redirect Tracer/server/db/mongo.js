const mongoose = require('mongoose');

const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://127.0.0.1:27017/voidonyx_tracer';

// Define full scan schema storing all trace & security header information
const ScanSchema = new mongoose.Schema({
  inputUrl: { type: String, required: true, index: true },
  startUrl: { type: String },
  finalUrl: { type: String },
  totalHops: { type: Number, default: 0 },
  totalTimeMs: { type: Number, default: 0 },
  loopDetected: { type: Boolean, default: false },
  maxHopsExceeded: { type: Boolean, default: false },
  securityScore: { type: Number, default: 0 },
  securityGrade: { type: String, default: 'F' },
  finalStatusCode: { type: Number, default: 0 },
  finalStatusText: { type: String, default: 'N/A' },
  chain: { type: Array, default: [] }, // Complete hop-by-hop sequence with headers
  securityAudit: { type: Object, default: {} }, // Full security audit & fix snippets
  clientIp: { type: String, default: '127.0.0.1' },
  userAgent: { type: String, default: '' },
  createdAt: { type: Date, default: Date.now, index: true }
});

const Scan = mongoose.models.Scan || mongoose.model('Scan', ScanSchema, 'scans');

let isConnected = false;

/**
 * Connect to MongoDB database
 */
async function connectMongoDB() {
  if (isConnected) return true;

  try {
    mongoose.set('strictQuery', false);
    await mongoose.connect(MONGODB_URI, {
      serverSelectionTimeoutMS: 3000
    });
    isConnected = true;
    console.log(`🍃 MongoDB connected: ${MONGODB_URI} (Database: voidonyx_tracer | Collection: scans)`);
    return true;
  } catch (err) {
    console.warn(`⚠️ MongoDB connection warning: ${err.message}. (Server using database fallback)`);
    isConnected = false;
    return false;
  }
}

/**
 * Save scan record into MongoDB Compass
 */
async function saveMongoScan(traceResult, clientIp = '127.0.0.1', userAgent = '') {
  if (!isConnected) return null;

  try {
    const finalHop = traceResult.chain ? traceResult.chain[traceResult.chain.length - 1] : null;

    const scanDoc = new Scan({
      inputUrl: traceResult.inputUrl,
      startUrl: traceResult.startUrl || traceResult.inputUrl,
      finalUrl: traceResult.finalUrl,
      totalHops: traceResult.totalHops,
      totalTimeMs: traceResult.totalTimeMs,
      loopDetected: traceResult.loopDetected || false,
      maxHopsExceeded: traceResult.maxHopsExceeded || false,
      securityScore: traceResult.securityAudit ? traceResult.securityAudit.score : 0,
      securityGrade: traceResult.securityAudit ? traceResult.securityAudit.grade : 'F',
      finalStatusCode: finalHop ? finalHop.statusCode : 0,
      finalStatusText: finalHop ? finalHop.statusText : 'N/A',
      chain: traceResult.chain || [],
      securityAudit: traceResult.securityAudit || {},
      clientIp,
      userAgent
    });

    const saved = await scanDoc.save();
    return saved;
  } catch (err) {
    console.error('Failed to save scan in MongoDB:', err.message);
    return null;
  }
}

/**
 * Fetch recent scan history records from MongoDB
 */
async function getMongoRecentHistory(limit = 20) {
  if (!isConnected) return null;

  try {
    const docs = await Scan.find({})
      .sort({ createdAt: -1 })
      .limit(limit)
      .lean();

    return docs.map(doc => ({
      id: doc._id.toString(),
      input_url: doc.inputUrl,
      final_url: doc.finalUrl,
      total_hops: doc.totalHops,
      total_time_ms: doc.totalTimeMs,
      security_score: doc.securityScore,
      security_grade: doc.securityGrade,
      final_status_code: doc.finalStatusCode,
      final_status_text: doc.finalStatusText,
      created_at: doc.createdAt.toISOString()
    }));
  } catch (err) {
    console.error('Failed to fetch history from MongoDB:', err.message);
    return null;
  }
}

/**
 * Fetch full scan document by ID from MongoDB
 */
async function getMongoScanById(id) {
  if (!isConnected) return null;

  try {
    if (!mongoose.Types.ObjectId.isValid(id)) {
      return null;
    }
    const doc = await Scan.findById(id).lean();
    if (!doc) return null;
    return {
      id: doc._id.toString(),
      inputUrl: doc.inputUrl,
      startUrl: doc.startUrl,
      finalUrl: doc.finalUrl,
      totalHops: doc.totalHops,
      totalTimeMs: doc.totalTimeMs,
      loopDetected: doc.loopDetected,
      maxHopsExceeded: doc.maxHopsExceeded,
      securityAudit: doc.securityAudit,
      chain: doc.chain,
      createdAt: doc.createdAt
    };
  } catch (err) {
    console.error(`Failed to fetch Mongo scan ID ${id}:`, err.message);
    return null;
  }
}

/**
 * Clear scans collection from MongoDB
 */
async function clearMongoHistory() {
  if (!isConnected) return false;

  try {
    await Scan.deleteMany({});
    return true;
  } catch (err) {
    console.error('Failed to clear MongoDB scans:', err.message);
    return false;
  }
}

/**
 * Get MongoDB analytical statistics
 */
async function getMongoStats() {
  if (!isConnected) return null;

  try {
    const totalTraces = await Scan.countDocuments({});
    if (totalTraces === 0) {
      return {
        total_traces: 0,
        avg_time_ms: 0,
        avg_hops: 0,
        grade_counts: { 'A+': 0, 'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0 }
      };
    }

    const aggregation = await Scan.aggregate([
      {
        $group: {
          _id: null,
          avgTime: { $avg: '$totalTimeMs' },
          avgHops: { $avg: '$totalHops' }
        }
      }
    ]);

    const gradeAgg = await Scan.aggregate([
      {
        $group: {
          _id: '$securityGrade',
          count: { $sum: 1 }
        }
      }
    ]);

    const gradeCounts = { 'A+': 0, 'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0 };
    gradeAgg.forEach(g => {
      if (g._id && gradeCounts[g._id] !== undefined) {
        gradeCounts[g._id] = g.count;
      }
    });

    const statsData = aggregation[0] || { avgTime: 0, avgHops: 0 };

    return {
      total_traces: totalTraces,
      avg_time_ms: Math.round(statsData.avgTime || 0),
      avg_hops: Number((statsData.avgHops || 0).toFixed(1)),
      grade_counts: gradeCounts
    };
  } catch (err) {
    console.error('Failed to calculate MongoDB stats:', err.message);
    return null;
  }
}

module.exports = {
  Scan,
  connectMongoDB,
  saveMongoScan,
  getMongoRecentHistory,
  getMongoScanById,
  clearMongoHistory,
  getMongoStats
};
