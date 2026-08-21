import { IDnsCache } from '../models/DnsCache';
import { DnsRecord } from './dohResolver';
export declare function getCachedResult(domain: string, type: string): Promise<IDnsCache | null>;
export declare function setCachedResult(domain: string, type: string, records: DnsRecord[], queryTimeMs: number): Promise<void>;
//# sourceMappingURL=cache.d.ts.map