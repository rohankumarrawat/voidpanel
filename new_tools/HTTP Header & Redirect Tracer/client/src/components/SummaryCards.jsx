import React from 'react';
import { Route, Clock, ShieldCheck, CheckCircle2, AlertTriangle, XCircle, BarChart3 } from 'lucide-react';

export default function SummaryCards({ data }) {
  if (!data) return null;

  const { totalHops, totalTimeMs, loopDetected, maxHopsExceeded, chain, securityAudit } = data;
  const finalHop = chain[chain.length - 1];
  const finalStatusCode = finalHop ? finalHop.statusCode : 0;
  const finalStatusText = finalHop ? finalHop.statusText : 'N/A';

  const gradeColors = {
    'A+': 'text-emerald-700 bg-emerald-50 border-emerald-200',
    'A': 'text-emerald-700 bg-emerald-50 border-emerald-200',
    'B': 'text-blue-700 bg-blue-50 border-blue-200',
    'C': 'text-amber-700 bg-amber-50 border-amber-200',
    'D': 'text-orange-700 bg-orange-50 border-orange-200',
    'F': 'text-rose-700 bg-rose-50 border-rose-200'
  };

  const currentGradeStyle = gradeColors[securityAudit.grade] || gradeColors['F'];
  const hopColors = ['bg-[#FF5C00]', 'bg-purple-600', 'bg-emerald-500', 'bg-amber-500', 'bg-blue-600', 'bg-rose-500'];

  return (
    <div className="space-y-4 my-6">
      {/* 4 Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Hops */}
        <div className="voidonyx-card p-5 flex items-center justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Total Hops</p>
            <div className="flex items-baseline space-x-2 mt-1">
              <span className="text-3xl font-extrabold text-slate-900 font-mono">{totalHops}</span>
              <span className="text-xs font-medium text-slate-500">
                {totalHops === 1 ? 'hop' : 'hops'}
              </span>
            </div>
            {loopDetected && (
              <p className="text-xs font-semibold text-rose-600 mt-1 flex items-center space-x-1">
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>Redirect Loop Detected!</span>
              </p>
            )}
            {maxHopsExceeded && (
              <p className="text-xs font-semibold text-amber-600 mt-1 flex items-center space-x-1">
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>Max 10 Hops Limit</span>
              </p>
            )}
          </div>
          <div className="p-3 bg-orange-50 text-[#FF5C00] rounded-2xl border border-orange-200 shadow-sm">
            <Route className="w-6 h-6" />
          </div>
        </div>

        {/* Card 2: Final Status */}
        <div className="voidonyx-card p-5 flex items-center justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Final HTTP Status</p>
            <div className="flex items-baseline space-x-2 mt-1">
              <span className="text-2xl font-extrabold font-mono text-slate-900">{finalStatusCode}</span>
              <span className="text-xs font-medium text-slate-600 truncate max-w-[100px]">
                {finalStatusText}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Destination response
            </p>
          </div>
          <div className={`p-3 rounded-2xl border shadow-sm ${finalStatusCode >= 200 && finalStatusCode < 300 ? 'bg-emerald-50 text-emerald-600 border-emerald-200' : 'bg-amber-50 text-amber-600 border-amber-200'}`}>
            {finalStatusCode >= 200 && finalStatusCode < 300 ? (
              <CheckCircle2 className="w-6 h-6" />
            ) : (
              <XCircle className="w-6 h-6" />
            )}
          </div>
        </div>

        {/* Card 3: Total Latency */}
        <div className="voidonyx-card p-5 flex items-center justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Total Latency</p>
            <div className="flex items-baseline space-x-1 mt-1">
              <span className="text-3xl font-extrabold text-slate-900 font-mono">{totalTimeMs}</span>
              <span className="text-xs font-medium text-slate-500">ms</span>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Cumulative resolution time
            </p>
          </div>
          <div className="p-3 bg-purple-50 text-purple-600 rounded-2xl border border-purple-200 shadow-sm">
            <Clock className="w-6 h-6" />
          </div>
        </div>

        {/* Card 4: Security Score */}
        <div className="voidonyx-card p-5 flex items-center justify-between">
          <div className="w-full">
            <div className="flex items-center justify-between">
              <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Security Grade</p>
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-extrabold border ${currentGradeStyle}`}>
                {securityAudit.grade} ({securityAudit.score}%)
              </span>
            </div>
            
            <div className="w-full bg-slate-100 h-2.5 rounded-full mt-3 overflow-hidden border border-slate-200">
              <div
                className={`h-full transition-all duration-700 ${
                  securityAudit.score >= 80 ? 'bg-emerald-500' : securityAudit.score >= 60 ? 'bg-[#FF5C00]' : securityAudit.score >= 40 ? 'bg-amber-500' : 'bg-rose-500'
                }`}
                style={{ width: `${securityAudit.score}%` }}
              />
            </div>

            <div className="flex justify-between text-[10px] text-slate-500 mt-2 font-mono font-bold">
              <span className="text-emerald-700">{securityAudit.summaryCounts.pass} Passed</span>
              <span className="text-amber-700">{securityAudit.summaryCounts.warn} Warn</span>
              <span className="text-rose-700">{securityAudit.summaryCounts.fail} Failed</span>
            </div>
          </div>
        </div>
      </div>

      {/* Per-Hop Latency Distribution Meter Bar (VoidOnyx Meter Style) */}
      {chain && chain.length > 1 && (
        <div className="voidonyx-card p-5 space-y-3">
          <div className="flex items-center justify-between text-xs text-slate-600">
            <span className="flex items-center space-x-2 font-bold text-slate-800">
              <BarChart3 className="w-4 h-4 text-[#FF5C00]" />
              <span>Latency Distribution Meter per Hop</span>
            </span>
            <span className="font-mono text-[11px] text-[#FF5C00] font-bold">{totalTimeMs} ms Total</span>
          </div>

          {/* VoidOnyx Orange Meter Bar */}
          <div className="w-full h-3.5 bg-slate-100 rounded-full overflow-hidden flex border border-slate-200 p-0.5">
            {chain.map((hop, idx) => {
              const percentage = Math.max((hop.responseTimeMs / (totalTimeMs || 1)) * 100, 3);
              const colorClass = hopColors[idx % hopColors.length];
              return (
                <div
                  key={idx}
                  className={`h-full ${colorClass} rounded-sm transition-all border-r border-white`}
                  style={{ width: `${percentage}%` }}
                  title={`Hop #${hop.hop}: ${hop.responseTimeMs} ms (${Math.round(percentage)}%)`}
                />
              );
            })}
          </div>

          <div className="flex flex-wrap gap-3 text-[11px] font-mono text-slate-600 pt-1">
            {chain.map((hop, idx) => {
              const colorClass = hopColors[idx % hopColors.length];
              return (
                <div key={idx} className="flex items-center space-x-1.5 font-semibold">
                  <span className={`w-2.5 h-2.5 rounded-full ${colorClass}`} />
                  <span>Hop #{hop.hop}: {hop.responseTimeMs}ms</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
