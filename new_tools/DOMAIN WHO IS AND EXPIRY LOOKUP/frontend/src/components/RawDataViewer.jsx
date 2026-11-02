import React, { useState } from 'react';
import { Code, Copy, Check, Terminal } from 'lucide-react';

export default function RawDataViewer({ rawData, normalizedData }) {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const formattedJson = JSON.stringify(normalizedData, null, 2);

  const handleCopy = () => {
    navigator.clipboard.writeText(formattedJson);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="border border-slate-200/90 rounded-2xl bg-white p-6 shadow-sm space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center space-x-2">
          <Terminal className="w-4 h-4 text-slate-700" />
          <span className="text-sm font-bold text-slate-900 font-mono">Developer Options & Raw Response</span>
        </div>

        <div className="flex items-center space-x-2">
          <button
            type="button"
            onClick={handleCopy}
            className="px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 border border-slate-200 text-xs font-mono text-slate-700 hover:text-slate-900 transition-all flex items-center space-x-1.5"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-600" />
                <span className="text-emerald-700 font-semibold">Copied JSON!</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                <span>Copy as JSON</span>
              </>
            )}
          </button>

          <button
            type="button"
            onClick={() => setIsOpen(!isOpen)}
            className="px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 border border-slate-200 text-xs font-mono text-slate-700 hover:text-slate-900 transition-all flex items-center space-x-1.5"
          >
            <Code className="w-3.5 h-3.5 text-rose-600" />
            <span>{isOpen ? 'Hide Raw Response' : 'View Raw Response'}</span>
          </button>
        </div>
      </div>

      {isOpen && (
        <div className="space-y-3 animate-fadeIn">
          <div className="p-4 rounded-xl bg-slate-900 text-slate-200 font-mono text-xs overflow-x-auto max-h-96 shadow-inner">
            <pre className="whitespace-pre-wrap leading-relaxed">
              {typeof rawData === 'string'
                ? rawData
                : JSON.stringify(rawData || normalizedData, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
