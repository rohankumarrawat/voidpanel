import React from 'react';
import { Activity, RefreshCw } from 'lucide-react';

export default function RecentChecks({ recentChecks = [], onSelectHost }) {
  if (!recentChecks || recentChecks.length === 0) return null;

  const getStatusBadge = (status) => {
    switch (status) {
      case 'valid':
        return { label: 'Valid', color: 'text-emerald-700 bg-emerald-50 border-emerald-200' };
      case 'expiring':
        return { label: 'Expiring', color: 'text-amber-700 bg-amber-50 border-amber-200' };
      case 'expired':
        return { label: 'Expired', color: 'text-red-700 bg-red-50 border-red-200' };
      case 'untrusted':
        return { label: 'Untrusted', color: 'text-red-700 bg-red-50 border-red-200' };
      default:
        return { label: 'Error', color: 'text-slate-600 bg-slate-100 border-slate-200' };
    }
  };

  return (
    <div className="bg-white rounded-3xl p-6 border border-slate-200/90 shadow-sm space-y-4">
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-red-500 animate-pulse" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Recent Public Lookups
          </h3>
        </div>
        <span className="text-xs font-medium text-slate-400">VoidOnyx Live Feed</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs font-medium">
        {recentChecks.map((item, idx) => {
          const badge = getStatusBadge(item.status);

          return (
            <div
              key={idx}
              onClick={() => onSelectHost(item.host, item.port || 443)}
              className="p-3.5 rounded-2xl bg-slate-50 hover:bg-slate-100 border border-slate-200/60 cursor-pointer transition-all flex flex-col justify-between group"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold text-slate-900 group-hover:text-red-600 truncate">
                  {item.host}
                </span>
                <span className={`px-2 py-0.5 rounded-full text-[10px] uppercase font-bold border ${badge.color}`}>
                  {badge.label}
                </span>
              </div>

              <div className="flex items-center justify-between text-[11px] text-slate-500">
                <span>{item.daysRemaining !== null ? `${item.daysRemaining} days left` : 'No cert'}</span>
                <RefreshCw className="w-3.5 h-3.5 text-slate-400 group-hover:text-red-500 transition-transform group-hover:rotate-180" />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

