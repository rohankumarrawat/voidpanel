import React, { useState } from 'react';
import { ShieldCheck, AlertTriangle, XCircle, Clock, Copy, Check, Database, Zap } from 'lucide-react';

export default function StatusBanner({ data }) {
  const [copiedJson, setCopiedJson] = useState(false);
  const [copiedPem, setCopiedPem] = useState(false);

  if (!data) return null;

  const { status, statusReason, daysRemaining, isCached, rawCertPem } = data;

  const getStatusBadge = () => {
    switch (status) {
      case 'valid':
        return {
          icon: ShieldCheck,
          label: 'VALID & TRUSTED',
          bg: 'bg-emerald-50 text-emerald-700 border-emerald-200',
        };
      case 'expiring':
        return {
          icon: AlertTriangle,
          label: 'EXPIRING SOON',
          bg: 'bg-amber-50 text-amber-700 border-amber-200',
        };
      case 'expired':
        return {
          icon: XCircle,
          label: 'CERTIFICATE EXPIRED',
          bg: 'bg-red-50 text-red-700 border-red-200',
        };
      case 'untrusted':
        return {
          icon: AlertTriangle,
          label: 'UNTRUSTED / SELF-SIGNED',
          bg: 'bg-red-50 text-red-700 border-red-200',
        };
      default:
        return {
          icon: XCircle,
          label: 'INSPECTION ERROR',
          bg: 'bg-slate-100 text-slate-700 border-slate-200',
        };
    }
  };

  const badge = getStatusBadge();
  const Icon = badge.icon;

  const getDaysColor = () => {
    if (daysRemaining === null || daysRemaining === undefined) return 'text-slate-400';
    if (daysRemaining <= 0) return 'text-red-600';
    if (daysRemaining <= 7) return 'text-red-500';
    if (daysRemaining <= 30) return 'text-amber-600';
    return 'text-emerald-600';
  };

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopiedJson(true);
    setTimeout(() => setCopiedJson(false), 2000);
  };

  const handleCopyPem = () => {
    if (rawCertPem) {
      navigator.clipboard.writeText(rawCertPem);
      setCopiedPem(true);
      setTimeout(() => setCopiedPem(false), 2000);
    }
  };

  return (
    <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200/90 shadow-sm relative overflow-hidden transition-all">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        
        {/* Left Column: Status Badge & Message */}
        <div className="space-y-3 flex-1">
          <div className="flex flex-wrap items-center gap-3">
            <span className={`inline-flex items-center gap-2 px-3 py-1 rounded-full border text-xs font-bold ${badge.bg}`}>
              <Icon className="w-4 h-4" />
              <span>{badge.label}</span>
            </span>

            {/* Cache Indicator */}
            {isCached ? (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200">
                <Database className="w-3.5 h-3.5 text-slate-500" />
                <span>Cached Result</span>
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                <Zap className="w-3.5 h-3.5 text-emerald-600" />
                <span>Live Socket Handshake</span>
              </span>
            )}
          </div>

          <div>
            <h3 className="text-2xl font-extrabold text-slate-900 flex items-center gap-2">
              <span>{data.host}</span>
              <span className="text-slate-400 font-normal text-base">:{data.port}</span>
            </h3>
            <p className="text-sm font-medium text-slate-500 mt-1">
              {statusReason}
            </p>
          </div>
        </div>

        {/* Center Column: Big Days Remaining Counter */}
        {daysRemaining !== null && daysRemaining !== undefined && (
          <div className="bg-slate-50 px-6 py-4 rounded-2xl border border-slate-200/80 text-center min-w-[170px]">
            <div className="text-xs font-medium uppercase tracking-wider text-slate-400 mb-1 flex items-center justify-center gap-1">
              <Clock className="w-3.5 h-3.5" /> Days Remaining
            </div>
            <div className={`text-4xl font-extrabold tracking-tight ${getDaysColor()}`}>
              {daysRemaining <= 0 ? 0 : daysRemaining}
            </div>
            <div className="text-xs font-medium text-slate-400 mt-1">
              {daysRemaining <= 0 ? 'Expired' : 'Until Expiry'}
            </div>
          </div>
        )}

        {/* Right Column: Developer Actions */}
        <div className="flex flex-col sm:flex-row md:flex-col gap-2 shrink-0">
          <button
            onClick={handleCopyJson}
            className="px-4 py-2 bg-slate-100 hover:bg-slate-200 border border-slate-200 rounded-xl text-xs font-semibold text-slate-700 flex items-center justify-center gap-2 transition-all"
          >
            {copiedJson ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4 text-slate-500" />}
            <span>{copiedJson ? 'Copied JSON!' : 'Copy as JSON'}</span>
          </button>

          {rawCertPem && (
            <button
              onClick={handleCopyPem}
              className="px-4 py-2 bg-slate-100 hover:bg-slate-200 border border-slate-200 rounded-xl text-xs font-semibold text-slate-700 flex items-center justify-center gap-2 transition-all"
            >
              {copiedPem ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4 text-slate-500" />}
              <span>{copiedPem ? 'Copied PEM!' : 'Copy Raw Cert'}</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

