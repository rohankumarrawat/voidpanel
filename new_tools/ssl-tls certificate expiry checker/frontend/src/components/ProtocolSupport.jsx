import React from 'react';
import { Cpu, ShieldCheck, Lock, AlertTriangle, Check } from 'lucide-react';

export default function ProtocolSupport({
  protocol = 'TLSv1.3',
  tlsVersionsSupported = ['TLSv1.3', 'TLSv1.2'],
  publicKey = {},
}) {
  const versions = [
    { name: 'TLSv1.3', label: 'TLS 1.3', modern: true, desc: 'Modern, highly secure handshake' },
    { name: 'TLSv1.2', label: 'TLS 1.2', modern: true, desc: 'Standard secure fallback' },
    { name: 'TLSv1.1', label: 'TLS 1.1', modern: false, desc: 'Deprecated / Vulnerable' },
    { name: 'TLSv1.0', label: 'TLS 1.0', modern: false, desc: 'Deprecated / Vulnerable' },
  ];

  return (
    <div className="space-y-4 font-mono text-xs">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        
        {/* Negotiated Active Protocol */}
        <div className="p-4 rounded-lg bg-void-950 border border-void-700/80 space-y-2">
          <div className="flex items-center gap-2 text-slate-400 font-semibold border-b border-void-800 pb-2">
            <Lock className="w-4 h-4 text-cyan-glow" />
            <span>Negotiated TLS Handshake</span>
          </div>
          <div className="pt-1 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Negotiated Protocol:</span>
              <span className="px-2.5 py-1 rounded bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/40 text-sm">
                {protocol}
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              The primary socket established a secure connection using {protocol}.
            </p>
          </div>
        </div>

        {/* Public Key Strength */}
        <div className="p-4 rounded-lg bg-void-950 border border-void-700/80 space-y-2">
          <div className="flex items-center gap-2 text-slate-400 font-semibold border-b border-void-800 pb-2">
            <Cpu className="w-4 h-4 text-cyan-glow" />
            <span>Asymmetric Encryption Key</span>
          </div>
          <div className="pt-1 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Key Specification:</span>
              <span className="text-slate-200 font-bold">
                {publicKey?.algorithm || 'RSA (2048-bit)'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Security Grade:</span>
              <span className="inline-flex items-center gap-1 text-emerald-400 font-bold bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                <ShieldCheck className="w-3.5 h-3.5" /> High Grade
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* TLS Version Support Matrix */}
      <div className="p-4 rounded-lg bg-void-950 border border-void-700/80 space-y-3">
        <div className="text-slate-400 font-semibold border-b border-void-800 pb-2">
          TLS Protocol Support Matrix
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {versions.map((ver) => {
            const isSupported = tlsVersionsSupported.includes(ver.name) || protocol === ver.name;

            return (
              <div
                key={ver.name}
                className={`p-3 rounded-lg border flex flex-col justify-between space-y-2 ${
                  isSupported
                    ? ver.modern
                      ? 'bg-emerald-500/10 border-emerald-500/30 text-slate-100'
                      : 'bg-amber-500/10 border-amber-500/30 text-slate-100'
                    : 'bg-void-900 border-void-800 text-slate-500 opacity-60'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold">{ver.label}</span>
                  {isSupported ? (
                    <span className="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
                      <Check className="w-3 h-3" />
                    </span>
                  ) : (
                    <span className="text-[10px] text-slate-500 uppercase">Disabled</span>
                  )}
                </div>
                <span className="text-[10px] block opacity-80">{ver.desc}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
