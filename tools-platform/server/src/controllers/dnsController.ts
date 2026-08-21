import { Request, Response, NextFunction } from 'express';
import crypto from 'crypto';
import { resolveRecords, LookupType } from '../services/dohResolver';
import { getCachedResult, setCachedResult } from '../services/cache';
import { LookupHistory } from '../models/LookupHistory';
import { ENV } from '../config/env';

function hashIP(ip: string): string {
  return crypto
    .createHash('sha256')
    .update(ip + ENV.IP_SALT)
    .digest('hex');
}

/**
 * GET /api/tools/dns?domain=example.com&type=ALL|A|AAAA|…
 */
export async function getDnsRecords(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const domain = (req.query.domain as string).trim().toLowerCase();
    const type = ((req.query.type as string | undefined) ?? 'ALL').toUpperCase() as LookupType;

    // 1. Cache check
    const cached = await getCachedResult(domain, type);
    if (cached) {
      res.json({
        domain,
        type,
        records: cached.records,
        cached: true,
        queryTimeMs: cached.queryTimeMs,
        isNxdomain: false,
      });
      return;
    }

    // 2. Live DoH resolution
    const startMs = Date.now();
    const { records, isNxdomain } = await resolveRecords(domain, type);
    const queryTimeMs = Date.now() - startMs;

    // 3. Determine overall status
    const hasFound = records.some((r) => r.status === 'found');
    const hasError = records.some((r) => r.status === 'error');
    const overallStatus: 'success' | 'not_found' | 'error' = hasFound
      ? 'success'
      : hasError
      ? 'error'
      : 'not_found';

    // 4. Persist to cache (non-blocking)
    void setCachedResult(domain, type, records, queryTimeMs);

    // 5. Write history entry
    const rawIP =
      (req.headers['x-forwarded-for'] as string | undefined)?.split(',')[0]?.trim() ??
      req.ip ??
      req.socket.remoteAddress ??
      'unknown';

    void LookupHistory.create({
      domain,
      type,
      status: overallStatus,
      timestamp: new Date(),
      ipHash: hashIP(rawIP),
    }).catch((err) => {
      console.warn('[History] Write failed (non-fatal):', (err as Error).message);
    });

    // 6. Respond
    res.json({ domain, type, records, cached: false, queryTimeMs, isNxdomain });
  } catch (err) {
    next(err);
  }
}
