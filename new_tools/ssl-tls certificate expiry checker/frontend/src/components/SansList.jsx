import React, { useState } from 'react';
import { Search, Copy, Check, ShieldCheck } from 'lucide-react';

export default function SansList({ sans = [], targetHost = '' }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [copied, setCopied] = useState(false);

  const filteredSans = sans.filter((san) =>
    san.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleCopyAll = () => {
    navigator.clipboard.writeText(sans.join('\n'));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!sans || sans.length === 0) {
    return (
      <div className="p-4 rounded-lg bg-void-950 border border-void-700 text-xs font-mono text-slate-500">
        No Subject Alternative Names (SANs) specified for this certificate.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Search & Actions Header */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-64">
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search SAN domains..."
            className="w-full pl-8 pr-3 py-1.5 bg-void-950 border border-void-700 rounded-lg text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-400"
          />
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
        </div>

        <button
          onClick={handleCopyAll}
          className="w-full sm:w-auto px-3 py-1.5 bg-void-850 hover:bg-void-700 border border-void-700 rounded-lg text-xs font-mono text-slate-300 flex items-center justify-center gap-1.5 transition-all"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-cyan-glow" />}
          <span>{copied ? 'Copied List!' : `Copy All (${sans.length})`}</span>
        </button>
      </div>

      {/* Grid of SANs */}
      <div className="max-h-60 overflow-y-auto pr-1 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 text-xs font-mono">
        {filteredSans.map((san, idx) => {
          const isTarget = targetHost.toLowerCase() === san.toLowerCase() ||
            (san.startsWith('*.') && targetHost.toLowerCase().endsWith(san.slice(2)));

          return (
            <div
              key={idx}
              className={`p-2.5 rounded-lg border flex items-center justify-between truncate transition-colors ${
                isTarget
                  ? 'bg-cyan-500/10 border-cyan-500/40 text-cyan-300 font-semibold'
                  : 'bg-void-950 border-void-700/60 text-slate-300 hover:border-void-600'
              }`}
            >
              <span className="truncate" title={san}>{san}</span>
              {isTarget && (
                <ShieldCheck className="w-3.5 h-3.5 text-cyan-glow shrink-0 ml-1" title="Target Match" />
              )}
            </div>
          );
        })}
      </div>

      {filteredSans.length === 0 && (
        <div className="p-4 text-center text-xs font-mono text-slate-500">
          No SANs matching "{searchTerm}"
        </div>
      )}
    </div>
  );
}
