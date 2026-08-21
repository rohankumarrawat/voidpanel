export type RecordType = 'ALL' | 'A' | 'AAAA' | 'MX' | 'CNAME' | 'NS' | 'TXT' | 'SOA' | 'CAA' | 'SRV'

export type RecordStatus = 'found' | 'not_found' | 'error'

export interface DnsRecordItem {
  id?: string
  type: RecordType | string
  host: string
  value: string
  ttl: number
  status: RecordStatus
  error?: string
}

export interface DnsApiResponse {
  domain: string
  records: DnsRecordItem[]
  queryTimeMs: number
  isNxdomain?: boolean
  error?: string
  cached?: boolean
}
