/**
 * DoH Resolver Service
 * Performs DNS-over-HTTPS lookups using:
 *   Primary:  Cloudflare → https://cloudflare-dns.com/dns-query
 *   Fallback: Google     → https://dns.google/resolve
 */
export type DnsRecordType = 'A' | 'AAAA' | 'CNAME' | 'MX' | 'NS' | 'TXT' | 'SOA' | 'CAA' | 'SRV';
export interface DohAnswer {
    name: string;
    type: number;
    TTL: number;
    data: string;
}
export interface DohResponse {
    Status: number;
    TC: boolean;
    RD: boolean;
    RA: boolean;
    AD: boolean;
    CD: boolean;
    Question?: Array<{
        name: string;
        type: number;
    }>;
    Answer?: DohAnswer[];
    Authority?: DohAnswer[];
    Comment?: string;
}
export type RecordStatus = 'found' | 'not_found' | 'error';
export interface DnsRecord {
    type: string;
    host: string;
    value: string;
    ttl: number;
    status: RecordStatus;
    error?: string;
}
export type LookupType = DnsRecordType | 'ALL';
export declare function resolveRecords(domain: string, type: LookupType): Promise<{
    records: DnsRecord[];
    isNxdomain: boolean;
}>;
//# sourceMappingURL=dohResolver.d.ts.map