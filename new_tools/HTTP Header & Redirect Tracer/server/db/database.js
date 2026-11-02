const fs = require('fs');
const path = require('path');
const {
  saveMongoScan,
  getMongoRecentHistory,
  getMongoScanById,
  clearMongoHistory,
  getMongoStats
} = require('./mongo');

const DB_DIR = path.join(__dirname, '../data');
const DB_FILE = path.join(DB_DIR, 'tracer_db.json');

/**
 * Ensures database directory and JSON storage file exist.
 */
function initDatabase() {
  try {
    if (!fs.existsSync(DB_DIR)) {
      fs.mkdirSync(DB_DIR, { recursive: true });
    }

    if (!fs.existsSync(DB_FILE)) {
      const initialData = {
        last_id: 0,
        trace_logs: []
      };
      fs.writeFileSync(DB_FILE, JSON.stringify(initialData, null, 2), 'utf8');
    }
  } catch (err) {
    console.error('Error initializing VoidOnyx database:', err.message);
  }
}

/**
 * Read data from database file safely.
 */
function readDB() {
  try {
    initDatabase();
    const raw = fs.readFileSync(DB_FILE, 'utf8');
    return JSON.parse(raw);
  } catch (err) {
    console.error('Failed to read VoidOnyx DB:', err.message);
    return { last_id: 0, trace_logs: [] };
  }
}

/**
 * Write data to database file atomically.
 */
function writeDB(data) {
  try {
    initDatabase();
    const tempFile = `${DB_FILE}.tmp`;
    fs.writeFileSync(tempFile, JSON.stringify(data, null, 2), 'utf8');
    fs.renameSync(tempFile, DB_FILE);
  } catch (err) {
    console.error('Failed to write VoidOnyx DB:', err.message);
  }
}

/**
 * Save a new trace log into BOTH MongoDB Compass and local file storage.
 */
async function saveTraceLog(traceResult, clientIp = '127.0.0.1', userAgent = '') {
  try {
    // 1. Save to MongoDB (MongoDB Compass)
    await saveMongoScan(traceResult, clientIp, userAgent);

    // 2. Save to local fallback DB
    const db = readDB();
    const newId = (db.last_id || 0) + 1;
    const finalHop = traceResult.chain ? traceResult.chain[traceResult.chain.length - 1] : null;

    const logEntry = {
      id: newId,
      input_url: traceResult.inputUrl,
      start_url: traceResult.startUrl || traceResult.inputUrl,
      final_url: traceResult.finalUrl,
      total_hops: traceResult.totalHops,
      total_time_ms: traceResult.totalTimeMs,
      loop_detected: traceResult.loopDetected || false,
      max_hops_exceeded: traceResult.maxHopsExceeded || false,
      security_score: traceResult.securityAudit ? traceResult.securityAudit.score : 0,
      security_grade: traceResult.securityAudit ? traceResult.securityAudit.grade : 'F',
      final_status_code: finalHop ? finalHop.statusCode : 0,
      final_status_text: finalHop ? finalHop.statusText : 'N/A',
      chain: traceResult.chain,
      security_audit: traceResult.securityAudit,
      user_agent: userAgent,
      client_ip: clientIp,
      created_at: new Date().toISOString()
    };

    db.trace_logs.unshift(logEntry);
    if (db.trace_logs.length > 500) {
      db.trace_logs = db.trace_logs.slice(0, 500);
    }
    db.last_id = newId;

    writeDB(db);
    return logEntry;
  } catch (err) {
    console.error('Error saving trace log to DB:', err.message);
    return null;
  }
}

/**
 * Get recent trace logs (tries MongoDB first, falls back to local DB).
 */
async function getRecentHistory(limit = 20) {
  try {
    const mongoHistory = await getMongoRecentHistory(limit);
    if (mongoHistory) return mongoHistory;

    const db = readDB();
    return db.trace_logs.slice(0, limit).map(entry => ({
      id: entry.id,
      input_url: entry.input_url,
      final_url: entry.final_url,
      total_hops: entry.total_hops,
      total_time_ms: entry.total_time_ms,
      security_score: entry.security_score,
      security_grade: entry.security_grade,
      final_status_code: entry.final_status_code,
      final_status_text: entry.final_status_text,
      created_at: entry.created_at
    }));
  } catch (err) {
    console.error('Error fetching recent history:', err.message);
    return [];
  }
}

/**
 * Get full trace log by ID (tries MongoDB first, falls back to local DB).
 */
async function getTraceById(id) {
  try {
    const mongoDoc = await getMongoScanById(id);
    if (mongoDoc) return mongoDoc;

    const db = readDB();
    const targetId = Number(id);
    return db.trace_logs.find(entry => entry.id === targetId) || null;
  } catch (err) {
    console.error(`Error fetching trace ID ${id}:`, err.message);
    return null;
  }
}

/**
 * Purge history records from MongoDB and local storage.
 */
async function clearHistory() {
  try {
    await clearMongoHistory();
    const db = readDB();
    db.trace_logs = [];
    writeDB(db);
    return true;
  } catch (err) {
    console.error('Error clearing DB history:', err.message);
    return false;
  }
}

/**
 * Get global analytical statistics (tries MongoDB first, falls back to local DB).
 */
async function getGlobalStats() {
  try {
    const mongoStats = await getMongoStats();
    if (mongoStats) return mongoStats;

    const db = readDB();
    const logs = db.trace_logs || [];
    const totalTraces = logs.length;

    if (totalTraces === 0) {
      return {
        total_traces: 0,
        avg_time_ms: 0,
        avg_hops: 0,
        grade_counts: { 'A+': 0, 'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0 }
      };
    }

    const sumTime = logs.reduce((acc, curr) => acc + (curr.total_time_ms || 0), 0);
    const sumHops = logs.reduce((acc, curr) => acc + (curr.total_hops || 0), 0);

    const gradeCounts = { 'A+': 0, 'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0 };
    logs.forEach(l => {
      if (l.security_grade && gradeCounts[l.security_grade] !== undefined) {
        gradeCounts[l.security_grade]++;
      }
    });

    return {
      total_traces: totalTraces,
      avg_time_ms: Math.round(sumTime / totalTraces),
      avg_hops: Number((sumHops / totalTraces).toFixed(1)),
      grade_counts: gradeCounts
    };
  } catch (err) {
    console.error('Error calculating global DB stats:', err.message);
    return { total_traces: 0, avg_time_ms: 0, avg_hops: 0, grade_counts: {} };
  }
}

module.exports = {
  initDatabase,
  saveTraceLog,
  getRecentHistory,
  getTraceById,
  clearHistory,
  getGlobalStats
};
