import { Request, Response } from 'express';
import mongoose from 'mongoose';
import os from 'os';

export function getHealthStatus(_req: Request, res: Response): void {
  const dbState = mongoose.connection.readyState;
  const dbStatus = dbState === 1 ? 'connected' : dbState === 2 ? 'connecting' : 'disconnected';

  res.json({
    status: 'ok',
    uptime: process.uptime(),
    timestamp: new Date().toISOString(),
    database: dbStatus,
    memory: {
      rss: Math.round(process.memoryUsage().rss / 1024 / 1024) + ' MB',
      heap: Math.round(process.memoryUsage().heapUsed / 1024 / 1024) + ' MB',
    },
    hostname: os.hostname(),
  });
}
