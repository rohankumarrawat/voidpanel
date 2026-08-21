import { useState, useRef, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { Globe, Shield, Sparkles, RefreshCw, Copy, Check, ArrowLeft, Search, Timer, Database, AlertTriangle, Loader2 } from 'lucide-react'
import { DnsApiResponse, DnsRecordItem, RecordType } from '../../lib/types'
import { buildDnsLookupUrl, normalizeDnsResponse } from '../../lib/api'

const INDIVIDUAL_TYPES: Exclude<RecordType, 'ALL'>[] = ['A', 'AAAA', 'MX', 'CNAME', 'NS', 'TXT', 'SOA', 'CAA', 'SRV']
const RECORD_TYPES: RecordType[] = ['ALL', ...INDIVIDUAL_TYPES]
const QUICK_DOMAINS = ['google.com', 'cloudflare.com', 'github.com', 'example.com']

const TYPE_COLORS: Record<string, string> = {
  A: 'bg-blue-100 text-blue-700',
  AAAA: 'bg-indigo-100 text-indigo-700',
  MX: 'bg-emerald-100 text-emerald-700',
  CNAME: 'bg-amber-100 text-amber-700',
  NS: 'bg-purple-100 text-purple-700',
  TXT: 'bg-slate-100 text-slate-700',
  SOA: 'bg-rose-100 text-rose-700',
  CAA: 'bg-cyan-100 text-cyan-700',
  SRV: 'bg-orange-100 text-orange-700',
}

interface StreamingState {
  domain: string
  pendingTypes: Set<string>
  records: DnsRecordItem[]
  queryTimeMs: number
  errors: string[]
  resolvedCount: number
  totalTypes: number
  cached: boolean
}

export default function DnsCheckerPage() {
  const [domain, setDomain] = useState('')
  const [selectedType, setSelectedType] = useState<RecordType>('ALL')
  const [streaming, setStreaming] = useState<StreamingState | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [copiedValue, setCopiedValue] = useState<string | null>(null)

  const abortRef = useRef<AbortController | null>(null)

  const executeLookup = useCallback(async (d: string, t: RecordType) => {
    if (!d.trim()) return

    if (abortRef.current) {
      abortRef.current.abort()
    }
    const controller = new AbortController()
    abortRef.current = controller

    const cleanDomain = d.trim().toLowerCase()
    setDomain(d)
    setSelectedType(t)
    setIsLoading(true)

    const typesToQuery = t === 'ALL' ? INDIVIDUAL_TYPES : [t]

    const initialState: StreamingState = {
      domain: cleanDomain,
      pendingTypes: new Set(typesToQuery),
      records: [],
      queryTimeMs: 0,
      errors: [],
      resolvedCount: 0,
      totalTypes: typesToQuery.length,
      cached: false,
    }
    setStreaming(initialState)

    const startMs = Date.now()

    const promises = typesToQuery.map(async (recordType) => {
      try {
        const response = await fetch(buildDnsLookupUrl(cleanDomain, recordType), {
          signal: controller.signal,
        })
        const raw = await response.json()
        const data = normalizeDnsResponse(raw, cleanDomain)

        if (controller.signal.aborted) return

        setStreaming((prev) => {
          if (!prev) return prev
          const newPending = new Set(prev.pendingTypes)
          newPending.delete(recordType)
          return {
            ...prev,
            pendingTypes: newPending,
            records: [...prev.records, ...data.records],
            queryTimeMs: Date.now() - startMs,
            resolvedCount: prev.resolvedCount + 1,
            cached: prev.cached || Boolean(data.cached),
            errors: data.error ? [...prev.errors, `${recordType}: ${data.error}`] : prev.errors,
          }
        })
      } catch (err: unknown) {
        if (controller.signal.aborted) return
        const message = err instanceof Error ? err.message : 'Unknown error'
        setStreaming((prev) => {
          if (!prev) return prev
          const newPending = new Set(prev.pendingTypes)
          newPending.delete(recordType)
          return {
            ...prev,
            pendingTypes: newPending,
            resolvedCount: prev.resolvedCount + 1,
            queryTimeMs: Date.now() - startMs,
            errors: [...prev.errors, `${recordType}: ${message}`],
          }
        })
      }
    })

    await Promise.allSettled(promises)

    if (!controller.signal.aborted) {
      setIsLoading(false)
      setStreaming((prev) => prev ? { ...prev, queryTimeMs: Date.now() - startMs } : prev)
    }
  }, [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!isLoading || domain.trim()) executeLookup(domain, selectedType)
  }

  const handleRefresh = () => {
    if (domain) executeLookup(domain, selectedType)
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopiedValue(text)
    setTimeout(() => setCopiedValue(null), 2000)
  }

  const foundRecords = streaming?.records.filter(r => r.status === 'found') ?? []
  const notFoundTypes = streaming?.records.filter(r => r.status === 'not_found').map(r => r.type) ?? []
  const hasResults = streaming !== null

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-8">
      <div className="flex items-center gap-2 text-sm text-neutral-500">
        <Link to="/" className="hover:text-primary-500 flex items-center gap-1">
          <ArrowLeft className="w-4 h-4" /> All Tools
        </Link>
        <span>/</span>
        <span className="font-semibold text-neutral-700">DNS Record Checker</span>
      </div>

      <div className="text-center space-y-3">
        <div className="mx-auto w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-lg shadow-primary-500/20">
          <Globe className="w-8 h-8 text-white" />
        </div>
        <h1 className="text-3xl sm:text-4xl font-black text-neutral-900">DNS Record Checker</h1>
        <p className="text-neutral-500 max-w-xl mx-auto">
          Lookup A, AAAA, MX, CNAME, NS, TXT, SOA, CAA, and SRV records for any domain using DNS-over-HTTPS.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-neutral-200 p-6 shadow-soft space-y-4">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" />
            <input
              type="text"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              placeholder="Enter domain name (e.g. google.com)"
              className="w-full pl-12 pr-4 py-3 bg-neutral-50 border border-neutral-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-400"
            />
          </div>
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value as RecordType)}
            className="px-4 py-3 bg-neutral-50 border border-neutral-200 rounded-xl text-sm font-medium focus:outline-none focus:ring-2 focus:ring-primary-500/30"
          >
            {RECORD_TYPES.map(t => (
              <option key={t} value={t}>{t === 'ALL' ? 'All Records' : t}</option>
            ))}
          </select>
          <button
            type="submit"
            disabled={!domain.trim()}
            className="px-6 py-3 bg-gradient-to-r from-primary-500 to-primary-600 text-white font-bold text-sm rounded-xl hover:shadow-lg hover:shadow-primary-500/25 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {isLoading ? (
              <span className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                Querying...
              </span>
            ) : 'Lookup DNS'}
          </button>
        </div>

        <div className="flex flex-wrap gap-2">
          <span className="text-xs text-neutral-400 font-medium self-center mr-1">Quick:</span>
          {QUICK_DOMAINS.map(d => (
            <button
              key={d}
              type="button"
              onClick={() => { setDomain(d); executeLookup(d, selectedType) }}
              className="px-3 py-1 text-xs font-medium bg-neutral-100 text-neutral-600 rounded-lg hover:bg-primary-50 hover:text-primary-600 transition-colors"
            >
              {d}
            </button>
          ))}
        </div>
      </form>

      {hasResults && streaming && (
        <div className="space-y-6 animate-fade-in-up">
          <div className="bg-white rounded-2xl border border-neutral-200 p-5 shadow-soft">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex flex-wrap items-center gap-6">
                <div className="flex items-center gap-2 text-sm">
                  <Globe className="w-4 h-4 text-primary-500" />
                  <span className="font-bold text-neutral-900">{streaming.domain}</span>
                </div>
                <div className="flex items-center gap-2 text-sm text-neutral-500">
                  <Timer className="w-4 h-4" />
                  <span>{streaming.queryTimeMs}ms</span>
                </div>
                {streaming.cached && (
                  <div className="flex items-center gap-2 text-sm text-amber-600">
                    <Database className="w-4 h-4" />
                    <span className="font-medium">Cached</span>
                  </div>
                )}
                <div className="text-sm">
                  <span className="font-bold text-emerald-600">{foundRecords.length}</span>
                  <span className="text-neutral-400"> records found</span>
                </div>

                {isLoading && (
                  <div className="flex items-center gap-2 text-sm text-primary-600">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span className="font-semibold">
                      {streaming.resolvedCount} of {streaming.totalTypes} types resolved
                    </span>
                  </div>
                )}
              </div>
              <button
                onClick={handleRefresh}
                disabled={isLoading}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-primary-600 bg-primary-50 rounded-lg hover:bg-primary-100 disabled:opacity-50 transition-colors"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>

            {isLoading && streaming.totalTypes > 1 && (
              <div className="mt-3">
                <div className="w-full bg-neutral-100 rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-gradient-to-r from-primary-400 to-primary-600 h-1.5 rounded-full transition-all duration-300 ease-out"
                    style={{ width: `${(streaming.resolvedCount / streaming.totalTypes) * 100}%` }}
                  />
                </div>
                <div className="flex flex-wrap gap-1.5 mt-2.5">
                  {INDIVIDUAL_TYPES.map(t => {
                    const isPending = streaming.pendingTypes.has(t)
                    const hasRecords = streaming.records.some(r => r.type === t && r.status === 'found')
                    const notFound = streaming.records.some(r => r.type === t && r.status === 'not_found')
                    return (
                      <span
                        key={t}
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold transition-all duration-200 ${
                          isPending
                            ? 'bg-neutral-100 text-neutral-400 animate-pulse'
                            : hasRecords
                            ? TYPE_COLORS[t] ?? 'bg-neutral-100 text-neutral-600'
                            : notFound
                            ? 'bg-neutral-50 text-neutral-300 line-through'
                            : 'bg-red-50 text-red-400'
                        }`}
                      >
                        {isPending && <Loader2 className="w-2.5 h-2.5 animate-spin" />}
                        {!isPending && hasRecords && <Check className="w-2.5 h-2.5" />}
                        {t}
                      </span>
                    )
                  })}
                </div>
              </div>
            )}
          </div>

          {streaming.errors.length > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-red-700 text-sm">Error</p>
                {streaming.errors.map((err, i) => (
                  <p key={i} className="text-sm text-red-600">{err}</p>
                ))}
              </div>
            </div>
          )}

          {foundRecords.length > 0 && (
            <div className="bg-white rounded-2xl border border-neutral-200 overflow-hidden shadow-soft">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-neutral-50 border-b border-neutral-200">
                      <th className="text-left px-5 py-3.5 font-bold text-neutral-600 text-xs uppercase tracking-wider">Type</th>
                      <th className="text-left px-5 py-3.5 font-bold text-neutral-600 text-xs uppercase tracking-wider">Host</th>
                      <th className="text-left px-5 py-3.5 font-bold text-neutral-600 text-xs uppercase tracking-wider">Value</th>
                      <th className="text-left px-5 py-3.5 font-bold text-neutral-600 text-xs uppercase tracking-wider">TTL</th>
                      <th className="text-center px-5 py-3.5 font-bold text-neutral-600 text-xs uppercase tracking-wider w-16"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {foundRecords.map((record, i) => (
                      <tr key={i} className="border-b border-neutral-100 hover:bg-neutral-50/50 transition-colors animate-fade-in-up" style={{ animationDelay: `${i * 30}ms` }}>
                        <td className="px-5 py-3.5">
                          <span className={`px-2.5 py-0.5 rounded-md text-xs font-bold ${TYPE_COLORS[record.type] ?? 'bg-neutral-100 text-neutral-600'}`}>
                            {record.type}
                          </span>
                        </td>
                        <td className="px-5 py-3.5 font-mono text-xs text-neutral-700 max-w-[200px] truncate">
                          {record.host}
                        </td>
                        <td className="px-5 py-3.5 font-mono text-xs text-neutral-700 max-w-[400px] break-all">
                          {record.value}
                        </td>
                        <td className="px-5 py-3.5 font-mono text-xs text-neutral-500">
                          {record.ttl}s
                        </td>
                        <td className="px-5 py-3.5 text-center">
                          <button
                            onClick={() => copyToClipboard(record.value)}
                            className="p-1.5 text-neutral-400 hover:text-primary-500 rounded-md hover:bg-primary-50 transition-colors"
                            title="Copy value"
                          >
                            {copiedValue === record.value
                              ? <Check className="w-3.5 h-3.5 text-emerald-500" />
                              : <Copy className="w-3.5 h-3.5" />
                            }
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {isLoading && foundRecords.length === 0 && (
            <div className="bg-white rounded-2xl border border-neutral-200 overflow-hidden shadow-soft p-6 space-y-4">
              {[1, 2, 3].map(i => (
                <div key={i} className="flex items-center gap-4 animate-pulse">
                  <div className="w-14 h-6 bg-neutral-200 rounded-md" />
                  <div className="w-32 h-4 bg-neutral-100 rounded" />
                  <div className="flex-1 h-4 bg-neutral-100 rounded" />
                  <div className="w-12 h-4 bg-neutral-100 rounded" />
                </div>
              ))}
            </div>
          )}

          {!isLoading && notFoundTypes.length > 0 && (
            <div className="bg-neutral-50 rounded-xl border border-neutral-200 p-4">
              <p className="text-sm text-neutral-500">
                <span className="font-semibold">No records found for:</span>{' '}
                {notFoundTypes.map(t => (
                  <span key={t} className="inline-block px-2 py-0.5 mx-0.5 rounded bg-neutral-200 text-xs font-mono font-bold text-neutral-600">
                    {t}
                  </span>
                ))}
              </p>
            </div>
          )}
        </div>
      )}

      {!hasResults && !isLoading && (
        <div className="bg-white rounded-2xl border border-neutral-200 p-12 shadow-soft text-center space-y-5">
          <div className="mx-auto w-20 h-20 rounded-3xl bg-primary-50 flex items-center justify-center shadow-sm">
            <Globe className="w-10 h-10 text-primary-500" />
          </div>
          <h2 className="text-2xl font-bold text-neutral-900">Ready to Query Live DNS Records</h2>
          <p className="text-neutral-500 max-w-lg mx-auto">
            Enter any domain name above (or click one of the quick presets) to inspect live A, AAAA, MX, CNAME, TXT, and NS records instantly via DoH.
          </p>
          <div className="flex flex-wrap justify-center gap-3 text-xs font-semibold text-neutral-600">
            <div className="inline-flex items-center gap-2 rounded-full border border-neutral-200 bg-neutral-100 px-3 py-2">
              <Shield className="w-4 h-4 text-primary-500" />
              Zero Data Exposure
            </div>
            <div className="inline-flex items-center gap-2 rounded-full border border-neutral-200 bg-neutral-100 px-3 py-2">
              <Sparkles className="w-4 h-4 text-amber-500" />
              Streaming Results
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
