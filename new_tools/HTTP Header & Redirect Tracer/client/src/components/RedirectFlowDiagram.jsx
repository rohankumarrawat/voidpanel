import React from 'react';
import { Lock, Unlock, ArrowRight, Clock, Zap } from 'lucide-react';

export default function RedirectFlowDiagram({ chain, selectedHop, onSelectHop }) {
  if (!chain || chain.length === 0) return null;

  return (
    <div className="voidonyx-card p-6 md:p-8 my-8">
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6 pb-4 border-b border-slate-200">
        <div>
          <h3 className="text-xl font-extrabold text-slate-900 flex items-center space-x-2">
            <Zap className="w-5 h-5 text-[#FF5C00]" />
            <span>Interactive Redirect Flow Visualizer</span>
          </h3>
          <p className="text-xs text-slate-500 mt-1 font-medium">
            Visual map of domain shifts, protocol upgrades (HTTP/HTTPS), status codes, and hop latency.
          </p>
        </div>
        <span className="px-3 py-1 bg-orange-50 border border-orange-200 text-[#FF5C00] text-xs font-bold font-mono rounded-xl shadow-sm">
          Click any node to inspect headers
        </span>
      </div>

      {/* Horizontal Flow Diagram for Desktop / Card Stack for Mobile */}
      <div className="relative overflow-x-auto pb-4 scrollbar-thin">
        <div className="flex flex-col md:flex-row items-stretch md:items-center gap-4 min-w-max p-2">
          {chain.map((step, idx) => {
            const isLast = idx === chain.length - 1;
            const isHttps = step.protocol === 'HTTPS';
            const isSelected = selectedHop && selectedHop.hop === step.hop;
            
            let hostname = step.url;
            try {
              hostname = new URL(step.url).hostname;
            } catch (e) {}

            return (
              <React.Fragment key={idx}>
                {/* Node Box */}
                <div
                  onClick={() => onSelectHop(step)}
                  className={`cursor-pointer group relative flex-1 min-w-[220px] max-w-[260px] rounded-2xl p-4 border transition-all duration-300 transform hover:-translate-y-1 ${
                    isSelected
                      ? 'bg-white border-[#FF5C00] ring-2 ring-[#FF5C00]/30 shadow-lg shadow-orange-500/15'
                      : 'bg-slate-50/80 border-slate-200 hover:border-[#FF5C00]/50 hover:bg-white'
                  }`}
                >
                  {/* Top Badge Row */}
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <span className="w-7 h-7 rounded-xl bg-slate-900 text-white flex items-center justify-center font-mono text-xs font-extrabold shadow-sm">
                      #{step.hop}
                    </span>

                    <span
                      className={`px-2.5 py-0.5 rounded-lg text-[11px] font-bold font-mono ${
                        step.statusCode === 301 || step.statusCode === 308
                          ? 'bg-sky-50 text-sky-700 border border-sky-200'
                          : step.statusCode === 302 || step.statusCode === 307
                          ? 'bg-amber-50 text-amber-700 border border-amber-200'
                          : step.statusCode >= 200 && step.statusCode < 300
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          : 'bg-rose-50 text-rose-700 border border-rose-200'
                      }`}
                    >
                      {step.statusCode} {step.statusText}
                    </span>
                  </div>

                  {/* Domain & URL info */}
                  <div className="space-y-1 mb-3">
                    <p className="text-xs font-bold text-slate-900 truncate font-mono" title={hostname}>
                      {hostname}
                    </p>
                    <p className="text-[10px] text-slate-500 truncate" title={step.url}>
                      {step.url}
                    </p>
                  </div>

                  {/* Protocol & Latency Badges */}
                  <div className="flex items-center justify-between pt-2 border-t border-slate-200 text-[10px] font-semibold">
                    <span className={`flex items-center space-x-1 ${isHttps ? 'text-emerald-700' : 'text-amber-700'}`}>
                      {isHttps ? <Lock className="w-3 h-3 text-emerald-600" /> : <Unlock className="w-3 h-3 text-amber-600" />}
                      <span>{step.protocol}</span>
                    </span>

                    <span className="flex items-center space-x-1 text-purple-700 font-mono">
                      <Clock className="w-3 h-3 text-purple-600" />
                      <span>{step.responseTimeMs} ms</span>
                    </span>
                  </div>
                </div>

                {/* Connector Arrow (Desktop) */}
                {!isLast && (
                  <div className="hidden md:flex flex-col items-center justify-center text-slate-400 px-1">
                    <ArrowRight className="w-5 h-5 text-[#FF5C00] animate-pulse" />
                    <span className="text-[9px] font-mono font-bold text-slate-400 mt-1">redirect</span>
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </div>
  );
}
