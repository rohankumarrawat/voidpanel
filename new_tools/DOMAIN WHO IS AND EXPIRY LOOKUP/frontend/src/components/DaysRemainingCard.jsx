import React from 'react';
import { Calendar, Clock, AlertCircle } from 'lucide-react';

export default function DaysRemainingCard({ daysRemaining, expiresDate, isAvailable }) {
  if (isAvailable) {
    return (
      <div className="bg-slate-50 border border-slate-200/80 rounded-2xl p-5 flex flex-col items-center justify-center text-center">
        <div className="w-12 h-12 rounded-full bg-blue-100 border border-blue-200 flex items-center justify-center mb-2">
          <Calendar className="w-6 h-6 text-blue-600" />
        </div>
        <span className="text-xs font-mono text-slate-500 uppercase tracking-wider">Registration Status</span>
        <span className="text-xl font-bold text-slate-900 mt-1">Ready for Registration</span>
        <p className="text-xs text-slate-500 mt-1 max-w-xs">
          This domain is not currently registered in WHOIS/RDAP registries.
        </p>
      </div>
    );
  }

  if (daysRemaining === null || daysRemaining === undefined) {
    return (
      <div className="bg-slate-50 border border-slate-200/80 rounded-2xl p-5 flex flex-col items-center justify-center text-center">
        <Clock className="w-6 h-6 text-slate-400 mb-2" />
        <span className="text-xs font-mono text-slate-500 uppercase">Expiry Status</span>
        <span className="text-base font-mono text-slate-700 mt-1">Expiration Date Not Exposed</span>
      </div>
    );
  }

  let colorClass = 'bg-emerald-50/80 border-emerald-200 text-emerald-900';
  let numberColor = 'text-emerald-700 bg-white border-emerald-200';
  let badgeText = 'Safe Expiration Window';

  if (daysRemaining <= 0) {
    colorClass = 'bg-red-50/80 border-red-200 text-red-900';
    numberColor = 'text-red-700 bg-white border-red-200';
    badgeText = 'Domain Has Expired!';
  } else if (daysRemaining <= 7) {
    colorClass = 'bg-red-50/80 border-red-200 text-red-900';
    numberColor = 'text-red-700 bg-white border-red-200';
    badgeText = 'Critical: Expiring in ≤7 Days';
  } else if (daysRemaining <= 30) {
    colorClass = 'bg-amber-50/80 border-amber-200 text-amber-900';
    numberColor = 'text-amber-700 bg-white border-amber-200';
    badgeText = 'Warning: Renewal Needed Soon';
  }

  return (
    <div className={`border rounded-2xl p-5 flex flex-col sm:flex-row items-center justify-between gap-4 transition-all ${colorClass}`}>
      <div className="flex items-center space-x-4 text-center sm:text-left">
        <div className={`w-16 h-16 rounded-2xl border flex flex-col items-center justify-center flex-shrink-0 ${numberColor}`}>
          <span className="text-2xl font-bold font-mono leading-none">
            {daysRemaining < 0 ? 0 : daysRemaining}
          </span>
          <span className="text-[10px] font-mono uppercase tracking-tighter text-slate-500 mt-0.5">Days</span>
        </div>

        <div>
          <span className="text-xs font-mono uppercase tracking-wider text-slate-500 block">Days Remaining</span>
          <div className="text-lg font-bold text-slate-900 tracking-tight flex items-center gap-2">
            {daysRemaining > 0 ? `${daysRemaining} days left until expiration` : 'Domain expired'}
          </div>
          <span className="text-xs font-mono text-slate-600 block mt-0.5">
            Expires on: {expiresDate ? new Date(expiresDate).toUTCString() : 'N/A'}
          </span>
        </div>
      </div>

      <div className="px-3.5 py-1.5 rounded-xl bg-white border border-slate-200 text-xs font-mono font-medium text-slate-700 flex items-center space-x-1.5 self-center shadow-sm">
        <AlertCircle className="w-3.5 h-3.5 text-slate-500" />
        <span>{badgeText}</span>
      </div>
    </div>
  );
}
