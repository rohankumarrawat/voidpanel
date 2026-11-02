import React, { useState } from 'react';
import { Search, Loader2, Sparkles, AlertCircle, Bot, ArrowRight, ShieldCheck } from 'lucide-react';

const PRESETS = [
  { label: '1.1.1.1 (Cloudflare)', url: 'http://1.1.1.1' },
  { label: '8.8.8.8 (Google)', url: 'http://8.8.8.8' },
  { label: 'google.com', url: 'http://google.com' },
  { label: 'github.com', url: 'http://github.com' }
];

const USER_AGENTS = [
  { label: 'Default VoidOnyx Engine', value: 'VoidOnyx-Redirect-Tracer/2.0' },
  { label: 'Googlebot Desktop', value: 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)' },
  { label: 'Googlebot Smartphone', value: 'Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.6533.119 Mobile Safari/537.36 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)' },
  { label: 'cURL CLI Agent', value: 'curl/8.4.0' }
];

export default function TraceInput({ onTrace, loading, error }) {
  const [url, setUrl] = useState('');
  const [selectedUA, setSelectedUA] = useState(USER_AGENTS[0].value);
  const [validationErr, setValidationErr] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!url.trim()) {
      setValidationErr('Please enter a URL, IPv4 address or domain to trace.');
      return;
    }
    setValidationErr('');
    onTrace(url.trim(), selectedUA);
  };

  const handlePreset = (presetUrl) => {
    setUrl(presetUrl);
    setValidationErr('');
    onTrace(presetUrl, selectedUA);
  };

  return (
    <div className="w-full max-w-5xl mx-auto my-8">
      {/* VoidOnyx Tools Hero Card */}
      <div className="bg-white rounded-3xl p-8 md:p-12 border border-slate-200/90 shadow-xl shadow-slate-200/50 relative overflow-hidden">
        
        {/* Tool Title & Subtitle */}
        <div className="mb-8">
          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
            HTTP Redirect & Header Tracer
          </h1>
          <p className="text-sm sm:text-base text-slate-500 mt-2 font-medium max-w-3xl leading-relaxed">
            Enter an IPv4 address, domain or URL to trace 301/302/307/308 redirect sequences & security headers in real-time.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Capsule Search Input & Vibrant Coral CTA Button */}
          <div className="relative flex items-center">
            <div className="absolute left-5 text-slate-400">
              <Search className="w-5 h-5" />
            </div>
            <input
              type="text"
              value={url}
              onChange={(e) => {
                setUrl(e.target.value);
                if (validationErr) setValidationErr('');
              }}
              placeholder="e.g. 1.1.1.1 or google.com or mail.yourdomain.com..."
              disabled={loading}
              className="w-full pl-14 pr-44 py-4 bg-[#F8FAFC] border border-slate-200 rounded-2xl text-slate-900 placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500/40 focus:border-rose-500 focus:bg-white transition-all font-mono"
            />
            <button
              type="submit"
              disabled={loading}
              className="absolute right-2.5 px-6 py-3 bg-gradient-to-r from-[#E11D48] to-[#F43F5E] hover:from-[#BE123C] hover:to-[#E11D48] text-white font-extrabold text-sm rounded-xl flex items-center space-x-2 transition-all shadow-md shadow-rose-500/25 disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Tracing...</span>
                </>
              ) : (
                <>
                  <ShieldCheck className="w-4 h-4" />
                  <span>Check Redirects</span>
                </>
              )}
            </button>
          </div>

          {/* User-Agent Switcher */}
          <div className="flex items-center space-x-3 bg-slate-50 p-2.5 rounded-xl border border-slate-200 text-xs">
            <Bot className="w-4 h-4 text-slate-500 shrink-0 ml-1" />
            <span className="text-slate-600 font-bold shrink-0">User-Agent Engine:</span>
            <select
              value={selectedUA}
              onChange={(e) => setSelectedUA(e.target.value)}
              className="bg-white text-slate-800 border border-slate-200 rounded-lg px-2.5 py-1 text-xs font-mono focus:outline-none focus:ring-1 focus:ring-rose-500 w-full font-medium"
            >
              {USER_AGENTS.map((ua, idx) => (
                <option key={idx} value={ua.value}>
                  {ua.label} ({ua.value.split('/')[0]})
                </option>
              ))}
            </select>
          </div>

          {(validationErr || error) && (
            <div className="flex items-center space-x-2 p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs font-semibold animate-pulse-slow">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
              <span>{validationErr || error}</span>
            </div>
          )}
        </form>

        {/* Quick Presets matching tools.voidonyx.in */}
        <div className="mt-6 pt-6 border-t border-slate-100 flex flex-wrap items-center gap-3 text-xs">
          <span className="font-semibold text-slate-500">Quick presets:</span>
          <div className="flex flex-wrap gap-2">
            {PRESETS.map((preset, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handlePreset(preset.url)}
                disabled={loading}
                className="px-3 py-1.5 rounded-xl bg-slate-100/80 border border-slate-200/80 hover:border-slate-300 hover:bg-slate-200/80 transition-all text-slate-700 font-mono font-medium disabled:opacity-50"
              >
                {preset.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
