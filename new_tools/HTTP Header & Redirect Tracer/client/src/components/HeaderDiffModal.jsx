import React, { useState } from 'react';
import { GitCompare, X, Plus, Minus, Edit3 } from 'lucide-react';

export default function HeaderDiffModal({ isOpen, onClose, chain }) {
  if (!isOpen || !chain || chain.length === 0) return null;

  const [hopAIdx, setHopAIdx] = useState(0);
  const [hopBIdx, setHopBIdx] = useState(chain.length > 1 ? chain.length - 1 : 0);

  const hopA = chain[hopAIdx];
  const hopB = chain[hopBIdx];

  const headersA = hopA ? hopA.headers || {} : {};
  const headersB = hopB ? hopB.headers || {} : {};

  const keysA = Object.keys(headersA);
  const keysB = Object.keys(headersB);
  const allKeys = Array.from(new Set([...keysA, ...keysB])).sort();

  const getDiffStatus = (key) => {
    const valA = headersA[key];
    const valB = headersB[key];

    if (valA === undefined && valB !== undefined) return 'ADDED';
    if (valA !== undefined && valB === undefined) return 'REMOVED';
    if (String(valA) !== String(valB)) return 'MODIFIED';
    return 'SAME';
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
      <div className="bg-white w-full max-w-4xl rounded-2xl p-6 border border-slate-200 shadow-2xl relative max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 pb-4 mb-4 shrink-0">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-xl bg-purple-50 text-purple-600 border border-purple-200">
              <GitCompare className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-extrabold text-slate-900">Response Header Diff & Comparison</h3>
              <p className="text-xs text-slate-500 font-medium">
                Compare HTTP header deltas between two specific hops in the redirect chain.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-xl text-slate-400 hover:text-slate-900 hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Hop Selectors */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4 bg-slate-50 p-3.5 rounded-xl border border-slate-200 text-xs shrink-0 font-medium">
          <div>
            <label className="block text-slate-600 font-bold mb-1">Hop A (Base Response):</label>
            <select
              value={hopAIdx}
              onChange={(e) => setHopAIdx(Number(e.target.value))}
              className="w-full bg-white border border-slate-200 rounded-lg p-2 text-slate-800 font-mono focus:outline-none focus:ring-1 focus:ring-[#FF5C00]"
            >
              {chain.map((step, idx) => (
                <option key={idx} value={idx}>
                  Hop #{step.hop}: {step.statusCode} ({step.protocol}) - {step.url}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-slate-600 font-bold mb-1">Hop B (Comparison Response):</label>
            <select
              value={hopBIdx}
              onChange={(e) => setHopBIdx(Number(e.target.value))}
              className="w-full bg-white border border-slate-200 rounded-lg p-2 text-slate-800 font-mono focus:outline-none focus:ring-1 focus:ring-[#FF5C00]"
            >
              {chain.map((step, idx) => (
                <option key={idx} value={idx}>
                  Hop #{step.hop}: {step.statusCode} ({step.protocol}) - {step.url}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Diff Table */}
        <div className="overflow-y-auto overflow-x-auto flex-1 rounded-xl border border-slate-200 scrollbar-thin">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-100 text-slate-700 uppercase text-[10px] tracking-wider border-b border-slate-200 sticky top-0 font-extrabold">
              <tr>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">Header Key</th>
                <th className="py-2.5 px-3">Hop #{hopA.hop} Value</th>
                <th className="py-2.5 px-3">Hop #{hopB.hop} Value</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white text-slate-800">
              {allKeys.map((key) => {
                const diff = getDiffStatus(key);
                const valA = headersA[key] !== undefined ? String(headersA[key]) : '—';
                const valB = headersB[key] !== undefined ? String(headersB[key]) : '—';

                return (
                  <tr
                    key={key}
                    className={`hover:bg-slate-50 transition-colors ${
                      diff === 'ADDED'
                        ? 'bg-emerald-50/70'
                        : diff === 'REMOVED'
                        ? 'bg-rose-50/70'
                        : diff === 'MODIFIED'
                        ? 'bg-amber-50/70'
                        : ''
                    }`}
                  >
                    <td className="py-2 px-3">
                      {diff === 'ADDED' && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-extrabold bg-emerald-100 text-emerald-800 border border-emerald-200 flex items-center space-x-1 w-max">
                          <Plus className="w-3 h-3" />
                          <span>ADDED</span>
                        </span>
                      )}
                      {diff === 'REMOVED' && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-extrabold bg-rose-100 text-rose-800 border border-rose-200 flex items-center space-x-1 w-max">
                          <Minus className="w-3 h-3" />
                          <span>REMOVED</span>
                        </span>
                      )}
                      {diff === 'MODIFIED' && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-extrabold bg-amber-100 text-amber-800 border border-amber-200 flex items-center space-x-1 w-max">
                          <Edit3 className="w-3 h-3" />
                          <span>MODIFIED</span>
                        </span>
                      )}
                      {diff === 'SAME' && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-600 flex items-center space-x-1 w-max">
                          <span>SAME</span>
                        </span>
                      )}
                    </td>
                    <td className="py-2 px-3 font-bold text-[#FF5C00] truncate max-w-[150px]" title={key}>
                      {key}
                    </td>
                    <td className="py-2 px-3 break-all text-slate-700 max-w-[200px]">{valA}</td>
                    <td className="py-2 px-3 break-all text-slate-700 max-w-[200px]">{valB}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Footer */}
        <div className="mt-4 pt-3 border-t border-slate-200 flex justify-end shrink-0">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-slate-100 hover:bg-slate-200 border border-slate-200 text-xs font-semibold text-slate-800 rounded-xl transition-colors"
          >
            Close Diff
          </button>
        </div>
      </div>
    </div>
  );
}
