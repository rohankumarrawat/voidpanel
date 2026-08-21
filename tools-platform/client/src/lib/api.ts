import { DnsApiResponse, RecordType } from './types'

export function buildDnsLookupUrl(domain: string, type: RecordType): string {
  const encodedDomain = encodeURIComponent(domain)
  const encodedType = encodeURIComponent(type)
  return `/api/tools/dns?domain=${encodedDomain}&type=${encodedType}`
}

export function normalizeDnsResponse(raw: unknown, domain: string): DnsApiResponse {
  if (!raw || typeof raw !== 'object') {
    return { domain, records: [], queryTimeMs: 0, error: 'Invalid response from DNS API.' }
  }

  const data = raw as Record<string, unknown>

  if (data.error === true && typeof data.message === 'string') {
    return {
      domain,
      records: [],
      queryTimeMs: typeof data.queryTimeMs === 'number' ? data.queryTimeMs : 0,
      error: data.message,
    }
  }

  return {
    domain: typeof data.domain === 'string' ? data.domain : domain,
    records: Array.isArray(data.records) ? data.records : [],
    queryTimeMs: typeof data.queryTimeMs === 'number' ? data.queryTimeMs : 0,
    isNxdomain: Boolean(data.isNxdomain),
    cached: Boolean(data.cached),
    error: typeof data.error === 'string' ? data.error : undefined,
  }
}
