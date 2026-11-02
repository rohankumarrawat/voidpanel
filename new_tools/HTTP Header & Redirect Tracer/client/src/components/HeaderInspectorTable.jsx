import React, { useState } from 'react';
import { Table, Search, Copy, Check, Download, FileSpreadsheet } from 'lucide-react';

export default function HeaderInspectorTable({ hop, fullResult }) {
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('ALL');
  const [copied, setCopied] = useState(false);

  if (!hop) return null;

  const headers = hop.headers || {};
  const entries = Object.entries(headers);

  const securityHeaderKeys = ['strict-transport-security', 'content-security-policy', 'x-frame-options', 'x-content-type-options', 'referrer-policy', 'permissions-policy', 'x-xss-protection'];
  const cacheHeaderKeys = ['cache-control', 'pragma', 'expires', 'etag', 'last-modified', 'age'];
  const serverHeaderKeys = ['server', 'via', 'x-powered-by', 'x-aspnet-version', 'x-served-by', 'cf-ray', 'server-timing'];

  const filteredEntries = entries.filter(([key, value]) => {
    const lowerKey = key.toLowerCase();
    const strVal = Array.isArray(value) ? value.join(' ') : String(value);

    if (categoryFilter === 'SECURITY' && !securityHeaderKeys.includes(lowerKey)) return false;
    if (categoryFilter === 'CACHE' && !cacheHeaderKeys.includes(lowerKey)) return false;
    if (categoryFilter === 'SERVER' && !serverHeaderKeys.includes(lowerKey)) return false;

    const query = search.toLowerCase();
    return lowerKey.includes(query) || strVal.toLowerCase().includes(query);
  });

  const copyMarkdownReport = () => {
    if (!fullResult) return;
    const lines = [
      `# HTTP Redirect & Security Header Report`,
      `**Initial URL:** ${fullResult.inputUrl}`,
      `**Final URL:** ${fullResult.finalUrl}`,
      `**Total Hops:** ${fullResult.totalHops}`,
      `**Total Latency:** ${fullResult.totalTimeMs} ms`,
      `**Security Score:** ${fullResult.securityAudit.score}% (Grade: ${fullResult.securityAudit.grade})`,
      ``,
      `## Redirect Hops Sequence`,
      ...fullResult.chain.map(h => `- Hop #${h.hop}: ${h.statusCode} ${h.statusText} -> ${h.url} (${h.responseTimeMs}ms)`),
      ``,
      `## Security Headers Audit`,
      ...fullResult.securityAudit.audits.map(a => `- **${a.header}**: ${a.status} (${a.summary})`)
    ];

    navigator.clipboard.writeText(lines.join('\n'));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const downloadJSON = () => {
    if (!fullResult) return;
    const jsonStr = JSON.stringify(fullResult, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `redirect-trace-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const downloadCSV = () => {
    if (!fullResult) return;
    let csvContent = 'Hop,Header_Name,Header_Value\n';
    fullResult.chain.forEach(h => {
      Object.entries(h.headers || {}).forEach(([k, v]) => {
        const valStr = Array.isArray(v) ? v.join('; ') : String(v);
        const escapedVal = `"${valStr.replace(/"/g, '""')}"`;
        csvContent += `${h.hop},"${k}",${escapedVal}\n`;
      });
    });

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `redirect-headers-${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="voidonyx-card p-6 md:p-8 my-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 pb-4 border-b border-slate-200">
        <div>
          <h3 className="text-xl font-extrabold text-slate-900 flex items-center space-x-2">
            <Table className="w-5 h-5 text-purple-600" />
            <span>Raw HTTP Response Headers Inspector</span>
          </h3>
          <p className="text-xs text-slate-500 mt-1 font-medium">
            Inspecting Hop #{hop.hop} ({hop.url})
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={copyMarkdownReport}
            className="px-3 py-1.5 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl text-xs font-semibold text-slate-700 flex items-center space-x-1.5 transition-all shadow-sm"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5 text-slate-500" />}
            <span>{copied ? 'Report Copied' : 'Copy MD'}</span>
          </button>

          <button
            type="button"
            onClick={downloadCSV}
            className="px-3 py-1.5 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl text-xs font-semibold text-slate-700 flex items-center space-x-1.5 transition-all shadow-sm"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
            <span>CSV</span>
          </button>

          <button
            type="button"
            onClick={downloadJSON}
            className="px-3 py-1.5 bg-orange-50 hover:bg-orange-100 border border-orange-200 rounded-xl text-xs font-bold text-[#FF5C00] flex items-center space-x-1.5 transition-all shadow-sm"
          >
            <Download className="w-3.5 h-3.5" />
            <span>JSON</span>
          </button>
        </div>
      </div>

      {/* Filter search bar & category filters */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 mb-4">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3.5 top-3 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter headers by key or value..."
            className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-[#FF5C00] font-mono shadow-inner"
          />
        </div>

        <div className="flex items-center space-x-1 bg-slate-100 p-1.5 rounded-xl border border-slate-200 text-[11px] shrink-0 font-extrabold shadow-inner">
          {['ALL', 'SECURITY', 'CACHE', 'SERVER'].map((cat) => (
            <button
              key={cat}
              type="button"
              onClick={() => setCategoryFilter(cat)}
              className={`px-2.5 py-1 rounded-lg font-bold transition-all ${
                categoryFilter === cat
                  ? 'bg-[#FF5C00] text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Headers Table */}
      <div className="overflow-x-auto rounded-2xl border border-slate-200 shadow-sm">
        <table className="w-full text-left text-xs font-mono">
          <thead className="bg-slate-100 text-slate-600 uppercase text-[10px] tracking-wider border-b border-slate-200 font-extrabold">
            <tr>
              <th className="py-3 px-4 w-1/3">Header Name</th>
              <th className="py-3 px-4 w-2/3">Header Value</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white text-slate-800">
            {filteredEntries.length === 0 ? (
              <tr>
                <td colSpan={2} className="py-8 text-center text-slate-500 font-sans font-medium">
                  No response headers match your filter criteria.
                </td>
              </tr>
            ) : (
              filteredEntries.map(([key, val], idx) => {
                const strVal = Array.isArray(val) ? val.join(', ') : String(val);
                return (
                  <tr key={idx} className="hover:bg-orange-50/40 transition-colors">
                    <td className="py-2.5 px-4 text-[#FF5C00] font-bold truncate max-w-[200px]" title={key}>
                      {key}
                    </td>
                    <td className="py-2.5 px-4 break-all text-slate-800 font-medium">
                      {strVal}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
