import React, { useState } from 'react';
import { ShieldCheck, ShieldAlert, AlertTriangle, Info, CheckCircle2, Copy, Check, Terminal } from 'lucide-react';

export default function SecurityHeaderAudit({ audit }) {
  const [activeSnippetTab, setActiveSnippetTab] = useState('nginx');
  const [copiedSnippetIdx, setCopiedSnippetIdx] = useState(null);

  if (!audit || !audit.audits) return null;

  const copySnippet = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedSnippetIdx(idx);
    setTimeout(() => setCopiedSnippetIdx(null), 2000);
  };

  const getStatusTag = (status) => {
    switch (status) {
      case 'PASS':
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-extrabold bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center space-x-1">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>PASS</span>
          </span>
        );
      case 'WARN':
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-extrabold bg-amber-50 text-amber-700 border border-amber-200 flex items-center space-x-1">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>WARNING</span>
          </span>
        );
      case 'FAIL':
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-extrabold bg-rose-50 text-rose-700 border border-rose-200 flex items-center space-x-1">
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>MISSING / FAIL</span>
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-extrabold bg-blue-50 text-blue-700 border border-blue-200 flex items-center space-x-1">
            <Info className="w-3.5 h-3.5" />
            <span>INFO</span>
          </span>
        );
    }
  };

  return (
    <div className="voidonyx-card p-6 md:p-8 my-8">
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6 pb-4 border-b border-slate-200">
        <div>
          <h3 className="text-xl font-extrabold text-slate-900 flex items-center space-x-2">
            <ShieldCheck className="w-5 h-5 text-[#FF5C00]" />
            <span>Security Header Audit & Remediation Guide</span>
          </h3>
          <p className="text-xs text-slate-500 mt-1 font-medium">
            Automated analysis of modern defense-in-depth headers on the final response.
          </p>
        </div>

        {/* Server Snippet Tab Selector */}
        <div className="flex items-center space-x-1 bg-slate-100 p-1.5 rounded-2xl border border-slate-200 text-xs shadow-inner">
          {['nginx', 'apache', 'express'].map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveSnippetTab(tab)}
              className={`px-3 py-1.5 rounded-xl capitalize font-extrabold transition-all ${
                activeSnippetTab === tab
                  ? 'btn-voidonyx-primary text-white shadow-md'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* Audit items grid */}
      <div className="space-y-4">
        {audit.audits.map((item, idx) => {
          const snippetText = item.snippets ? item.snippets[activeSnippetTab] : null;

          return (
            <div
              key={idx}
              className={`rounded-2xl p-5 border transition-all ${
                item.status === 'PASS'
                  ? 'bg-slate-50/60 border-slate-200'
                  : item.status === 'WARN'
                  ? 'bg-amber-50/40 border-amber-200'
                  : 'bg-rose-50/40 border-rose-200'
              }`}
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-2">
                <div className="flex items-center space-x-3">
                  <h4 className="text-sm font-extrabold text-slate-900 font-mono">{item.header}</h4>
                  <span className="text-xs text-slate-500 hidden sm:inline font-medium">({item.name})</span>
                </div>
                {getStatusTag(item.status)}
              </div>

              <p className="text-xs text-slate-700 font-semibold mb-2">
                {item.summary}: <span className="text-slate-500 font-normal">{item.description}</span>
              </p>

              {item.value && (
                <div className="text-xs font-mono bg-slate-900 p-2.5 rounded-xl text-cyan-300 border border-slate-800 mb-3 break-all shadow-inner">
                  <span className="text-slate-500 select-none">Raw Header: </span>
                  {item.value}
                </div>
              )}

              {item.status !== 'PASS' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3 pt-3 border-t border-slate-200 text-xs">
                  <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 font-medium">
                    <span className="font-extrabold block mb-1 text-rose-900">⚠️ Vulnerability Risk:</span>
                    {item.risk}
                  </div>
                  <div className="p-3 rounded-xl bg-orange-50 border border-orange-200 text-orange-900 font-medium">
                    <span className="font-extrabold block mb-1 text-[#FF5C00]">💡 Remediation Advice:</span>
                    {item.recommendation}
                  </div>
                </div>
              )}

              {/* Code Snippet for Fix */}
              {snippetText && (
                <div className="mt-3 pt-3 border-t border-slate-200">
                  <div className="flex items-center justify-between text-xs text-slate-600 mb-1.5 font-mono font-bold">
                    <span className="flex items-center space-x-1.5">
                      <Terminal className="w-3.5 h-3.5 text-[#FF5C00]" />
                      <span>{activeSnippetTab.toUpperCase()} Configuration Fix:</span>
                    </span>
                    <button
                      type="button"
                      onClick={() => copySnippet(snippetText, idx)}
                      className="text-slate-500 hover:text-[#FF5C00] transition-colors flex items-center space-x-1 font-semibold"
                    >
                      {copiedSnippetIdx === idx ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-emerald-600" />
                          <span className="text-emerald-600">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5" />
                          <span>Copy</span>
                        </>
                      )}
                    </button>
                  </div>
                  <pre className="p-3 rounded-xl bg-slate-950 text-cyan-300 font-mono text-xs overflow-x-auto border border-slate-800 shadow-inner">
                    {snippetText}
                  </pre>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
