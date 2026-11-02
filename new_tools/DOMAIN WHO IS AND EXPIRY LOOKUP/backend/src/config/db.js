const mongoose = require('mongoose');

let isConnected = false;

const connectDB = async (uri = process.env.MONGODB_URI, retries = 5, delay = 2000) => {
  if (isConnected && mongoose.connection.readyState === 1) {
    return mongoose.connection;
  }

  const mongoUri = uri || 'mongodb://localhost:27017/voidonyx_whois';

  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      const conn = await mongoose.connect(mongoUri, {
        serverSelectionTimeoutMS: 5000,
      });
      isConnected = true;
      console.log(`[Database] MongoDB connected: ${conn.connection.host}/${conn.connection.name}`);
      return conn;
    } catch (err) {
      console.warn(`[Database] MongoDB connection attempt ${attempt}/${retries} failed: ${err.message}`);
      if (attempt === retries) {
        console.error('[Database] All MongoDB connection attempts exhausted. Operating in fallback mode if available.');
        return null;
      }
      await new Promise((res) => setTimeout(res, delay));
    }
  }
};

const disconnectDB = async () => {
  if (mongoose.connection.readyState !== 0) {
    await mongoose.disconnect();
    isConnected = false;
    console.log('[Database] MongoDB disconnected');
  }
};

module.exports = { connectDB, disconnectDB };
