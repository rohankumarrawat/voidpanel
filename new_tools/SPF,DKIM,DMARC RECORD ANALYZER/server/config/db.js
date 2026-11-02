import mongoose from 'mongoose';

let isConnected = false;

export async function connectDB() {
  const mongoUri = process.env.MONGO_URI || 'mongodb://127.0.0.1:27017/spf_dkim_dmarc_db';
  try {
    mongoose.set('strictQuery', true);
    await mongoose.connect(mongoUri, {
      serverSelectionTimeoutMS: 3000,
    });
    isConnected = true;
    console.log(`[MongoDB] Connected successfully to ${mongoUri}`);
  } catch (error) {
    isConnected = false;
    console.warn(`[MongoDB] Database connection skipped or failed: ${error.message}. Running in memory fallback mode.`);
  }
}

export function isMongoConnected() {
  return isConnected && mongoose.connection.readyState === 1;
}
