const mongoose = require('mongoose');
const env = require('../config/env');

let isConnected = false;

async function connectDB(uri = env.MONGODB_URI, maxRetries = 3) {
  if (isConnected && mongoose.connection.readyState === 1) {
    return mongoose.connection;
  }

  let retries = 0;
  while (retries < maxRetries) {
    try {
      console.log(`Connecting to MongoDB (Attempt ${retries + 1}/${maxRetries})...`);
      await mongoose.connect(uri, {
        serverSelectionTimeoutMS: 5000,
      });
      isConnected = true;
      console.log('✅ MongoDB connected successfully.');
      return mongoose.connection;
    } catch (err) {
      retries += 1;
      console.error(`❌ MongoDB connection attempt ${retries} failed:`, err.message);
      if (retries < maxRetries) {
        await new Promise((resolve) => setTimeout(resolve, 2000));
      } else {
        console.warn('⚠️ Warning: Proceeding without MongoDB persistent connection (Fallback mode).');
      }
    }
  }
  return null;
}

async function disconnectDB() {
  if (mongoose.connection.readyState !== 0) {
    await mongoose.disconnect();
    isConnected = false;
    console.log('MongoDB disconnected.');
  }
}

module.exports = { connectDB, disconnectDB };
