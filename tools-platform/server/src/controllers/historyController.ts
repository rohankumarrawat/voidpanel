import { Request, Response } from 'express';
import { LookupHistory } from '../models/LookupHistory';

export async function getRecentHistory(req: Request, res: Response): Promise<void> {
  try {
    const limit = Math.min(parseInt(req.query.limit as string) || 20, 100);
    const recent = await LookupHistory.find()
      .sort({ timestamp: -1 })
      .limit(limit)
      .select('-ipHash')
      .lean();
    res.json({ history: recent });
  } catch (err) {
    res.status(500).json({ error: true, message: 'Failed to fetch history.' });
  }
}
