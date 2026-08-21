import mongoose from 'mongoose';
import { ENV } from './env';

export async function connectDB(): Promise<void> {
  try {
    mongoose.set('strictQuery', true);
    await mongoose.connect(ENV.MONGODB_URI, { serverSelectionTimeoutMS: 5000 });
    console.log(`[DB] MongoDB connected → ${ENV.MONGODB_URI.replace(/\/\/.*@/, '//<credentials>@')}`);
  } catch (err) {
    console.warn('[DB] MongoDB unavailable — running without caching/history.');
    console.warn('[DB] Error:', (err as Error).message);
    // Don't crash — tools work without DB, just without caching
  }
}

// Gracefully close on process exit
process.on('SIGINT', async () => {
  await mongoose.connection.close();
  console.log('[DB] Connection closed on SIGINT');
  process.exit(0);
});
