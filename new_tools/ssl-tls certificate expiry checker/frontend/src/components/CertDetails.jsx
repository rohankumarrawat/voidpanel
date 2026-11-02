import React from 'react';
import { FileText, Key, Calendar, ShieldAlert, CheckCircle, Hash } from 'lucide-react';

export default function CertDetails({ data }) {
  if (!data) return null;

  const {
    validity,
    subject,
    issuer,
    serialNumber,
    fingerprintSha256,
    publicKey,
    signatureAlgorithm,
    hostnameMatch,
    host,
  } = data;

  const formatDate = (isoStr) => {
    if (!isoStr) return 'N/A';
    const date = new Date(isoStr);
    return `${date.toUTCString()} (${date.toLocaleDateString()})`;
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
      
      {/* Validity Window */}
      <div className="p-4 rounded-lg bg-void-950 border border-void-700/80 space-y-2">
        <div className="flex items-center gap-2 text-slate-400 font-semibold border-b border-void-800 pb-2">
          <Calendar className="w-4 h-4 text-cyan-glow" />
          <span>Validity Window</span>
        </div>
        <div className="space-y-1.5 pt-1">
          <div>
            <span className="text-slate-500 block">Valid From (notBefore):</span>
            <span className="text-slate-200">{formatDate(validity?.notBefore)}</span>
          </div>
          <div>
            <span className="text-slate-500 block">Valid Until (notAfter):</span>
            <span className="text-slate-200">{formatDate(validity?.notAfter)}</span>
          </div>
        </div>
      </div>

      {/* Hostname & SAN Match */}
      <div className="p-4 rounded-lg bg-void-950 border border-void-700/80 space-y-2">
        <div className="flex items-center gap-2 text-slate-400 font-semibold border-b border-void-800 pb-2">
          <ShieldAlert className="w-4 h-4 text-cyan-glow" />
          <span>Hostname Coverage</span>
        </div>
        <div className="pt-1 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-slate-500">Target Host:</span>
            <span className="text-cyan-300 font-bold">{host}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-500">SAN Coverage Status:</span>
            {hostnameMatch ? (
              <span className="inline-flex items-center gap-1 text-emerald-400 font-semibold bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                <CheckCircle className="w-3.5 h-3.5" /> Matched
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-ruby-400 font-semibold bg-ruby-500/10 px-2 py-0.5 rounded border border-ruby-500/20">
                <ShieldAlert className="w-3.5 h-3.5" /> Host Mismatch!
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Subject Information */}
      <div className="p-4 rounded-lg bg-void-950 border border-void-700/80 space-y-2">
        <div className="flex items-center gap-2 text-slate-400 font-semibold border-b border-void-800 pb-2">
          <FileText className="w-4 h-4 text-cyan-glow" />
          <span>Subject (Owner)</span>
        </div>
        <div className="space-y-1 pt-1">
          <div>
            <span className="text-slate-500">Common Name (CN):</span>
            <span className="text-slate-200 block truncate">{subject?.cn || 'N/A'}</span>
          </div>
          <div>
            <span className="text-slate-500">Organization (O):</span>
            <span className="text-slate-200 block truncate">{subject?.o || 'N/A'}</span>
          </div>
        </div>
      </div>

      {/* Issuer Information */}
      <div className="p-4 rounded-lg bg-void-950 border border-void-700/80 space-y-2">
        <div className="flex items-center gap-2 text-slate-400 font-semibold border-b border-void-800 pb-2">
          <FileText className="w-4 h-4 text-cyan-glow" />
          <span>Issuer (Certificate Authority)</span>
        </div>
        <div className="space-y-1 pt-1">
          <div>
            <span className="text-slate-500">CA Common Name (CN):</span>
            <span className="text-slate-200 block truncate">{issuer?.cn || 'N/A'}</span>
          </div>
          <div>
            <span className="text-slate-500">CA Organization (O):</span>
            <span className="text-slate-200 block truncate">{issuer?.o || 'N/A'}</span>
          </div>
        </div>
      </div>

      {/* Cryptography & Keys */}
      <div className="p-4 rounded-lg bg-void-950 border border-void-700/80 space-y-2 md:col-span-2">
        <div className="flex items-center gap-2 text-slate-400 font-semibold border-b border-void-800 pb-2">
          <Key className="w-4 h-4 text-cyan-glow" />
          <span>Cryptographic Properties</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-1">
          <div>
            <span className="text-slate-500 block">Public Key Algorithm:</span>
            <span className="text-cyan-300 font-semibold">{publicKey?.algorithm || 'N/A'}</span>
          </div>
          <div>
            <span className="text-slate-500 block">Signature Algorithm:</span>
            <span className="text-slate-200">{signatureAlgorithm || 'N/A'}</span>
          </div>
          <div>
            <span className="text-slate-500 block">Serial Number:</span>
            <span className="text-slate-200 font-mono text-[11px] truncate block">{serialNumber || 'N/A'}</span>
          </div>
        </div>
      </div>

      {/* SHA-256 Fingerprint */}
      <div className="p-4 rounded-lg bg-void-950 border border-void-700/80 space-y-2 md:col-span-2">
        <div className="flex items-center gap-2 text-slate-400 font-semibold border-b border-void-800 pb-2">
          <Hash className="w-4 h-4 text-cyan-glow" />
          <span>SHA-256 Fingerprint</span>
        </div>
        <div className="pt-1">
          <code className="p-2.5 rounded bg-void-900 border border-void-700/60 block text-[11px] text-cyan-glow break-all">
            {fingerprintSha256 || 'N/A'}
          </code>
        </div>
      </div>
    </div>
  );
}
