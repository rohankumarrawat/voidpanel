import React, { useState } from 'react';
import { Terminal, Copy, Check, X } from 'lucide-react';

export default function CurlGeneratorModal({ isOpen, onClose, traceData, hop }) {
  const [activeTab, setActiveTab] = useState('curl-il');
  const [copied, setCopied] = useState(false);

  if (!isOpen || !traceData) return null;

  const targetUrl = hop ? hop.url : traceData.inputUrl;

  const snippets = {
    'curl-il': `curl -IL "${targetUrl}"`,
    'curl-v': `curl -v -L "${targetUrl}"`,
    'python': `import requests

url = "${targetUrl}"
response = requests.get(url, allow_redirects=True)

print(f"Final Status Code: {response.status_code}")
print(f"Final Destination: {response.url}")
print("Redirect History:")
for resp in response.history:
    print(f" - [{resp.status_code}] {resp.url}")
`,
    'node': `const traceUrl = async (url) => {
  const res = await fetch(url, { redirect: 'follow' });
  console.log('Final Status:', res.status);
  console.log('Final URL:', res.url);
};

traceUrl("${targetUrl}");`
  };

  const currentSnippet = snippets[activeTab] || snippets['curl-il'];

  const copyToClipboard = () => {
    navigator.clipboard.writeText(currentSnippet);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
      <div className="bg-white w-full max-w-2xl rounded-2xl p-6 border border-slate-200 shadow-2xl relative">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-slate-200 pb-4 mb-4">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-xl bg-orange-50 text-[#FF5C00] border border-orange-200">
              <Terminal className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-extrabold text-slate-900">CLI Script & cURL Generator</h3>
              <p className="text-xs text-slate-500 font-medium">
                {hop ? `Generating request snippet for Hop #${hop.hop}` : 'Generating full trace script'}
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

        {/* Tab Buttons */}
        <div className="flex flex-wrap gap-2 mb-4 bg-slate-100 p-1.5 rounded-xl border border-slate-200 text-xs shadow-inner">
          <button
            type="button"
            onClick={() => setActiveTab('curl-il')}
            className={`px-3 py-1.5 rounded-lg font-mono font-extrabold transition-all ${
              activeTab === 'curl-il' ? 'btn-voidonyx-primary text-white shadow-sm' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            curl -IL
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('curl-v')}
            className={`px-3 py-1.5 rounded-lg font-mono font-extrabold transition-all ${
              activeTab === 'curl-v' ? 'btn-voidonyx-primary text-white shadow-sm' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            curl -v -L
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('python')}
            className={`px-3 py-1.5 rounded-lg font-mono font-extrabold transition-all ${
              activeTab === 'python' ? 'btn-voidonyx-primary text-white shadow-sm' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Python (requests)
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('node')}
            className={`px-3 py-1.5 rounded-lg font-mono font-extrabold transition-all ${
              activeTab === 'node' ? 'btn-voidonyx-primary text-white shadow-sm' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Node.js (fetch)
          </button>
        </div>

        {/* Snippet Code Display */}
        <div className="relative">
          <pre className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs font-mono text-cyan-300 overflow-x-auto max-h-64 scrollbar-thin shadow-inner">
            {currentSnippet}
          </pre>
          <button
            type="button"
            onClick={copyToClipboard}
            className="absolute top-3 right-3 px-3 py-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded-lg text-xs font-mono text-white flex items-center space-x-1.5 transition-all shadow"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Copied' : 'Copy Script'}</span>
          </button>
        </div>

        <div className="mt-4 pt-3 border-t border-slate-200 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-slate-100 hover:bg-slate-200 border border-slate-200 text-xs font-semibold text-slate-800 rounded-xl transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
