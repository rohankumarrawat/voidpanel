import React, { useState } from 'react';
import { Route, ArrowDown, Lock, Unlock, Clock, Copy, Check, ChevronDown, ChevronRight } from 'lucide-react';

export default function RedirectChainView({ chain, onSelectHopHeaders }) {
  const [copiedUrlIndex, setCopiedUrlIndex] = useState(null);
  const [expandedHop, setExpandedHop] = useState(null);

  if (!chain || chain.length === 0) return null;

  const copyToClipboard = (text, index) => {
    navigator.clipboard.writeText(text);
    setCopiedUrlIndex(index);
    setTimeout(() => setCopiedUrlIndex(null), 2000);
  };

  const getStatusBadgeClass = (code) => {
    if (code === 301 || code === 308) return 'status-301';
    if (code === 302 || code === 307) return 'status-302';
    if (code >= 200 && code < 300) return 'status-200';
    return 'status-400';
  };

  const getStatusDescription = (code) => {
    switch (code) {
      case 301: return 'Moved Permanently (Cached by browsers & passes SEO equity)';
      case 302: return 'Found / Temporary Redirect (Does not pass full link authority)';
      case 307: return 'Temporary Redirect (Preserves original HTTP request method like POST)';
      case 308: return 'Permanent Redirect (Preserves original HTTP request method like POST)';
      case 200: return '200 OK (Final Destination)';
      case 404: return '404 Not Found (Broken destination link)';
      default: return `HTTP Status ${code}`;
    }
  };

  return (
    <div className="voidonyx-card p-6 md:p-8 my-8">
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6 pb-4 border-b border-slate-200">
        <div>
          <h3 className="text-xl font-extrabold text-slate-900 flex items-center space-x-2">
            <Route className="w-5 h-5 text-[#FF5C00]" />
            <span>Redirect Chain Execution Timeline</span>
          </h3>
          <p className="text-xs text-slate-500 mt-1 font-medium">
            Step-by-step resolution from initial request URL to final HTTP response.
          </p>
        </div>
        <span className="px-3 py-1 bg-slate-100 border border-slate-200 rounded-xl text-xs font-mono font-bold text-slate-700 shadow-sm">
          {chain.length} {chain.length === 1 ? 'Hop' : 'Hops Total'}
        </span>
      </div>

      <div className="relative space-y-6">
        {chain.map((step, idx) => {
          const isLast = idx === chain.length - 1;
          const isHttps = step.protocol === 'HTTPS';
          const isExpanded = expandedHop === idx;

          return (
            <div key={idx} className="relative group">
              {/* Connector line between hops */}
              {!isLast && (
                <div className="absolute left-6 top-14 bottom-0 w-0.5 bg-gradient-to-b from-[#FF5C00] to-slate-200 -mb-6 z-0" />
              )}

              <div className="relative z-10 bg-white rounded-2xl p-5 border border-slate-200/90 hover:border-[#FF5C00]/50 transition-all shadow-sm">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  
                  {/* Left: Hop counter & status badge */}
                  <div className="flex items-start space-x-4">
                    <div className="w-10 h-10 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center font-mono text-sm font-extrabold text-white shrink-0 shadow-sm">
                      #{step.hop}
                    </div>

                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`px-2.5 py-0.5 rounded-lg text-xs font-extrabold font-mono ${getStatusBadgeClass(step.statusCode)}`}>
                          {step.statusCode} {step.statusText}
                        </span>

                        <span className={`px-2.5 py-0.5 rounded-lg text-[11px] font-bold flex items-center space-x-1 ${isHttps ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-amber-50 text-amber-700 border border-amber-200'}`}>
                          {isHttps ? <Lock className="w-3 h-3 text-emerald-600" /> : <Unlock className="w-3 h-3 text-amber-600" />}
                          <span>{step.protocol}</span>
                        </span>

                        <span className="px-2 py-0.5 rounded-lg bg-slate-100 text-slate-700 border border-slate-200 text-[11px] font-mono font-semibold flex items-center space-x-1">
                          <Clock className="w-3 h-3 text-purple-600" />
                          <span>{step.responseTimeMs} ms</span>
                        </span>
                      </div>

                      <div className="flex items-center space-x-2 pt-1">
                        <span className="font-mono text-sm text-slate-900 break-all select-all font-bold">
                          {step.url}
                        </span>
                        <button
                          type="button"
                          onClick={() => copyToClipboard(step.url, idx)}
                          className="text-slate-400 hover:text-[#FF5C00] transition-colors p-1"
                          title="Copy URL"
                        >
                          {copiedUrlIndex === idx ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                      </div>

                      <p className="text-xs text-slate-500 font-medium">
                        {getStatusDescription(step.statusCode)}
                      </p>
                    </div>
                  </div>

                  {/* Right: Actions */}
                  <div className="flex items-center space-x-2 self-start md:self-center shrink-0">
                    <button
                      type="button"
                      onClick={() => onSelectHopHeaders(step)}
                      className="px-3 py-1.5 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl text-xs font-semibold text-slate-700 hover:text-[#FF5C00] transition-all flex items-center space-x-1.5 shadow-sm"
                    >
                      <span>Headers</span>
                      <span className="px-1.5 py-0.2 bg-slate-900 rounded text-[10px] text-white font-mono font-bold">
                        {Object.keys(step.headers || {}).length}
                      </span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setExpandedHop(isExpanded ? null : idx)}
                      className="p-1.5 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl text-xs text-slate-500 hover:text-[#FF5C00] transition-all shadow-sm"
                    >
                      {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {/* Location target preview */}
                {step.location && (
                  <div className="mt-3 pt-3 border-t border-slate-100 flex items-center space-x-2 text-xs font-mono text-[#FF5C00] font-semibold bg-orange-50/60 px-3 py-2 rounded-xl border border-orange-100">
                    <ArrowDown className="w-3.5 h-3.5 text-[#FF5C00] shrink-0" />
                    <span className="text-slate-600 font-sans font-medium">Redirect Location:</span>
                    <span className="truncate">{step.location}</span>
                  </div>
                )}

                {/* Inline Header Inspector Dropdown */}
                {isExpanded && (
                  <div className="mt-4 pt-4 border-t border-slate-200 text-xs font-mono bg-slate-950 text-cyan-300 rounded-xl p-4 max-h-60 overflow-y-auto space-y-1 shadow-inner">
                    <div className="text-slate-400 font-sans font-bold mb-2 flex justify-between">
                      <span>HTTP Response Headers ({step.url})</span>
                    </div>
                    {Object.entries(step.headers || {}).map(([key, val]) => (
                      <div key={key} className="flex">
                        <span className="text-[#FF5C00] w-44 shrink-0 truncate font-semibold">{key}:</span>
                        <span className="text-slate-300 break-all">{Array.isArray(val) ? val.join(', ') : val}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
