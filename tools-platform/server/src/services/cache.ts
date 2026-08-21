import { DnsCache, IDnsCache } from '../models/DnsCache';
import { DnsRecord } from './dohResolver';

export async function getCachedResult(
  domain: string,
  type: string
): Promise<IDnsCache | null> {
  try {
    return await DnsCache.findOne({ domain, type }).lean<IDnsCache>();
  } catch {
    return null;
  }
}

export async function setCachedResult(
  domain: string,
  type: string,
  records: DnsRecord[],
  queryTimeMs: number
): Promise<void> {
  try {
    await DnsCache.findOneAndUpdate(
      { domain, type },
      { domain, type, records, queryTimeMs, createdAt: new Date() },
      { upsert: true, new: true }
    );
  } catch (err) {
    console.warn('[Cache] Write failed (non-fatal):', (err as Error).message);
  }
}
