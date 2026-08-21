import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Search, Sparkles, Zap, Shield, ArrowRight } from 'lucide-react'

interface ToolMeta {
  slug: string; name: string; description: string; category: string; icon: string
  status: 'live' | 'beta' | 'coming-soon'; path: string
}

const CATEGORIES = ['All', 'DNS & Domain', 'SSL & Security', 'Networking', 'Email', 'Marketing']
const STATUS_STYLES: Record<string, string> = {
  'live': 'bg-emerald-100 text-emerald-700',
  'beta': 'bg-amber-100 text-amber-700',
  'coming-soon': 'bg-ox-bg-alt text-ox-muted',
}
const STATUS_LABELS: Record<string, string> = { 'live': 'Live', 'beta': 'Beta', 'coming-soon': 'Coming Soon' }

const FALLBACK_TOOLS: ToolMeta[] = [
  { slug: 'dns-checker', name: 'DNS Record Checker', description: 'Lookup A, MX, TXT, CNAME, NS, and more DNS records for any domain via DoH.', category: 'DNS & Domain', icon: '🌐', status: 'live', path: '/tools/dns-checker' },
  { slug: 'whois-lookup', name: 'WHOIS Lookup', description: 'Get registration details, nameservers, and expiry date for any domain.', category: 'DNS & Domain', icon: '🔍', status: 'coming-soon', path: '/tools/whois-lookup' },
  { slug: 'ip-lookup', name: 'IP Geolocation', description: 'Find the geographic location, ISP, and ASN info for any IP address.', category: 'Networking', icon: '📍', status: 'coming-soon', path: '/tools/ip-lookup' },
  { slug: 'ssl-checker', name: 'SSL Certificate Checker', description: 'Verify SSL/TLS certificates, expiry dates, chain validity, and cipher strength.', category: 'SSL & Security', icon: '🔒', status: 'coming-soon', path: '/tools/ssl-checker' },
  { slug: 'mx-lookup', name: 'MX Record Lookup', description: 'Check mail exchange records, priorities, and email deliverability for a domain.', category: 'Email', icon: '📧', status: 'coming-soon', path: '/tools/mx-lookup' },
  { slug: 'spf-validator', name: 'SPF Record Validator', description: 'Validate SPF records and check DNS-based sender authorization for email.', category: 'Email', icon: '🛡️', status: 'coming-soon', path: '/tools/spf-validator' },
  { slug: 'http-headers', name: 'HTTP Header Inspector', description: 'Inspect HTTP response headers, security headers, and server configuration.', category: 'SSL & Security', icon: '🔬', status: 'coming-soon', path: '/tools/http-headers' },
  { slug: 'utm-builder', name: 'UTM Link Builder', description: 'Generate UTM-tagged campaign URLs for Google Analytics tracking.', category: 'Marketing', icon: '🔗', status: 'coming-soon', path: '/tools/utm-builder' },
]

export default function HomePage() {
  const [tools, setTools] = useState<ToolMeta[]>(FALLBACK_TOOLS)
  const [activeCategory, setActiveCategory] = useState('All')
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    fetch('/api/tools/registry')
      .then(r => r.json())
      .then(data => { if (data.tools?.length) setTools(data.tools) })
      .catch(() => {})
  }, [])

  const filteredTools = tools.filter(tool => {
    const matchesCategory = activeCategory === 'All' || tool.category === activeCategory
    const matchesSearch = searchQuery === '' ||
      tool.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tool.description.toLowerCase().includes(searchQuery.toLowerCase())
    return matchesCategory && matchesSearch
  })

  const liveCount = tools.filter(t => t.status === 'live').length

  return (
    <div className="max-w-[1200px] mx-auto px-[5%] py-14 space-y-14">
      {/* ── Hero ──────────────────────────────────────────── */}
      <section className="text-center space-y-7 animate-fade-in-up" style={{ paddingTop: 24 }}>
        <div className="inline-flex items-center gap-2 bg-white border border-black/10 rounded-full px-3.5 py-1.5 text-[0.76rem] font-bold text-ox-navy/70 shadow-ox-sm">
          <span className="bg-ox-brand text-white px-2.5 py-0.5 rounded-full text-[0.68rem] font-extrabold uppercase tracking-wider">New</span>
          {liveCount} Tool{liveCount !== 1 ? 's' : ''} Live · {tools.length} Total
        </div>

        <h1 className="text-[clamp(2.4rem,5vw,4rem)] font-black tracking-[-0.04em] leading-[1.06] text-ox-navy">
          Free Tools for{' '}
          <span className="bg-ox-brand bg-clip-text text-transparent">Developers & Admins</span>
        </h1>

        <p className="max-w-2xl mx-auto text-[1.05rem] leading-[1.75] text-ox-muted">
          Production-grade DNS, SSL, email, and marketing tools — completely free. Zero sign-up required.
          <br />
          <span className="text-ox-faint">Powered by VoidPanel.</span>
        </p>

        <div className="flex flex-wrap justify-center gap-4 text-sm font-semibold text-ox-muted">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white border border-black/10 shadow-ox-sm">
            <Zap className="w-4 h-4 text-ox-blue" />
            Real-Time Results
          </div>
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white border border-black/10 shadow-ox-sm">
            <Shield className="w-4 h-4 text-emerald-500" />
            No Data Stored
          </div>
        </div>
      </section>

      {/* ── Search ────────────────────────────────────────── */}
      <section className="max-w-xl mx-auto">
        <div className="relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-ox-faint" />
          <input
            type="text"
            placeholder="Search tools... (e.g. DNS, SSL, email)"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="w-full pl-12 pr-4 py-3.5 bg-white border border-black/10 rounded-ox-md text-sm focus:outline-none focus:ring-2 focus:ring-ox-blue/30 focus:border-ox-blue shadow-ox-sm transition-all"
          />
        </div>
      </section>

      {/* ── Category Tabs ─────────────────────────────────── */}
      <section className="flex flex-wrap justify-center gap-2">
        {CATEGORIES.map(cat => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={`px-4 py-2 rounded-ox-sm text-sm font-bold transition-all ${
              activeCategory === cat
                ? 'bg-ox-brand text-white shadow-ox-blue'
                : 'bg-white text-ox-muted border border-black/10 hover:border-ox-blue hover:text-ox-blue'
            }`}
          >
            {cat}
          </button>
        ))}
      </section>

      {/* ── Tools Grid ────────────────────────────────────── */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
        {filteredTools.map((tool, i) => (
          <Link
            key={tool.slug}
            to={tool.status === 'live' ? tool.path : `/tools/${tool.slug}`}
            className="group relative bg-white rounded-ox-lg border border-black/10 p-6 hover:shadow-ox-lg hover:border-ox-blue/30 transition-all duration-200 animate-fade-in-up"
            style={{ animationDelay: `${i * 50}ms` }}
          >
            <div className="absolute top-4 right-4">
              <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider ${STATUS_STYLES[tool.status]}`}>
                {STATUS_LABELS[tool.status]}
              </span>
            </div>

            <div className="w-12 h-12 rounded-ox-md bg-ox-bg-alt flex items-center justify-center text-2xl mb-4 group-hover:scale-110 transition-transform">
              {tool.icon}
            </div>

            <h3 className="font-bold text-ox-navy mb-1.5 group-hover:text-ox-blue transition-colors">
              {tool.name}
            </h3>

            <p className="text-sm text-ox-muted leading-relaxed mb-4">
              {tool.description}
            </p>

            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-ox-blue bg-blue-50 px-2.5 py-1 rounded-ox-sm">
                {tool.category}
              </span>
              {tool.status === 'live' && (
                <ArrowRight className="w-4 h-4 text-ox-faint group-hover:text-ox-blue group-hover:translate-x-1 transition-all" />
              )}
            </div>
          </Link>
        ))}
      </section>

      {filteredTools.length === 0 && (
        <div className="text-center py-16 text-ox-faint">
          <p className="text-lg font-medium">No tools found matching "{searchQuery}"</p>
          <p className="text-sm mt-2">Try a different search term or category</p>
        </div>
      )}
    </div>
  )
}
