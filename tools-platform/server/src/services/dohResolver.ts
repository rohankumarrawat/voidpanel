/**
 * DoH Resolver Service
 * Performs DNS-over-HTTPS lookups using:
 *   Primary:  Cloudflare → https://cloudflare-dns.com/dns-query
 *   Fallback: Google     → https://dns.google/resolve
 */

import axios, { AxiosError } from 'axios';

const DOH_CLOUDFLARE = 'https://cloudflare-dns.com/dns-query';
const DOH_GOOGLE = 'https://dns.google/resolve';
const TIMEOUT_MS = 5_000;

const ALL_RECORD_TYPES: DnsRecordType[] = [
  'A', 'AAAA', 'CNAME', 'MX', 'NS', 'TXT', 'SOA', 'CAA', 'SRV',
];

const TYPE_TO_NUM: Record<string, number> = {
  A: 1, NS: 2, CNAME: 5, SOA: 6, MX: 15, TXT: 16, AAAA: 28, SRV: 33, CAA: 257,
};

const NUM_TO_TYPE: Record<number, string> = Object.fromEntries(
  Object.entries(TYPE_TO_NUM).map(([k, v]) => [v, k])
);

export type DnsRecordType =
  | 'A' | 'AAAA' | 'CNAME' | 'MX' | 'NS' | 'TXT' | 'SOA' | 'CAA' | 'SRV';

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
  Question?: Array<{ name: string; type: number }>;
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

async function queryEndpoint(
  url: string,
  domain: string,
  type: string
): Promise<DohResponse> {
  const response = await axios.get<DohResponse>(url, {
    params: { name: domain, type },
    headers: { Accept: 'application/dns-json' },
    timeout: TIMEOUT_MS,
  });
  return response.data;
}

async function resolveType(domain: string, type: DnsRecordType): Promise<DnsRecord[]> {
  let data: DohResponse;

  try {
    data = await queryEndpoint(DOH_CLOUDFLARE, domain, type);
  } catch {
    try {
      data = await queryEndpoint(DOH_GOOGLE, domain, type);
    } catch (fallbackErr) {
      const isTimeout =
        axios.isAxiosError(fallbackErr) &&
        (fallbackErr as AxiosError).code === 'ECONNABORTED';

      return [
        {
          type,
          host: domain,
          value: '',
          ttl: 0,
          status: 'error',
          error: isTimeout
            ? 'DNS query timed out on both Cloudflare and Google DoH'
            : 'Failed to reach Cloudflare and Google DoH providers',
        },
      ];
    }
  }

  if (!data.Answer || data.Answer.length === 0) {
    return [{ type, host: domain, value: '', ttl: 0, status: 'not_found' }];
  }

  return data.Answer.map((answer) => ({
    type: NUM_TO_TYPE[answer.type] ?? type,
    host: answer.name.replace(/\.$/, ''),
    value: answer.data.replace(/\.$/, ''),
    ttl: answer.TTL,
    status: 'found' as RecordStatus,
  }));
}

export type LookupType = DnsRecordType | 'ALL';

export async function resolveRecords(
  domain: string,
  type: LookupType
): Promise<{ records: DnsRecord[]; isNxdomain: boolean }> {
  const types: DnsRecordType[] = type === 'ALL' ? ALL_RECORD_TYPES : [type as DnsRecordType];

  const settled = await Promise.allSettled(types.map((t) => resolveType(domain, t)));

  const records: DnsRecord[] = [];

  for (const result of settled) {
    if (result.status === 'fulfilled') {
      records.push(...result.value);
    } else {
      records.push({
        type: 'UNKNOWN',
        host: domain,
        value: '',
        ttl: 0,
        status: 'error',
        error: String(result.reason),
      });
    }
  }

  const allNotFound = records.every((r) => r.status === 'not_found');
  const isNxdomain = type === 'ALL' && allNotFound;

  return { records, isNxdomain };
}
