import React, { useState } from 'react';
import { Search, RefreshCw, AlertTriangle, ShieldCheck } from 'lucide-react';

const PRESET_DOMAINS = [
  { label: 'voidonyx.in', value: 'voidonyx.in' },
  { label: 'voidpanel.com', value: 'voidpanel.com' },
  { label: 'google.com', value: 'google.com' },
  { label: 'github.com', value: 'github.com' },
];

export default function DomainInput({ onSearch, isLoading, initialValue = '' }) {
  const [input, setInput] = useState(initialValue);
  const [validationError, setValidationError] = useState('');
  const [forceRefresh, setForceRefresh] = useState(false);

  const validateInput = (value) => {
    if (!value || !value.trim()) {
      return 'Please enter a domain name.';
    }

    let cleaned = value.trim().toLowerCase();
    cleaned = cleaned.replace(/^[a-zA-Z]+:\/\//, '').split('/')[0].split('?')[0].split(':')[0];

    if (cleaned.startsWith('www.')) {
      cleaned = cleaned.substring(4);
    }

    // IP address check
    const ipv4Regex = /^(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
    if (ipv4Regex.test(cleaned)) {
      return 'IP address detected. WHOIS lookup is for domain names only. Please use our RBL/IP Checker tool for IP addresses.';
    }

    const domainRegex = /^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$/;
    if (!domainRegex.test(cleaned) && !cleaned.startsWith('xn--')) {
      return 'Invalid domain syntax. Example format: voidonyx.in, voidpanel.com';
    }

    return null;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const err = validateInput(input);
    if (err) {
      setValidationError(err);
      return;
    }

    setValidationError('');
    onSearch(input, forceRefresh);
  };

  const handlePresetClick = (domain) => {
    setInput(domain);
    setValidationError('');
    onSearch(domain, false);
  };

  return (
    <div className="w-full max-w-4xl mx-auto">
      <div className="bg-white border border-slate-200/90 rounded-[24px] p-6 sm:p-8 shadow-card space-y-6">
        <div className="space-y-1 text-left">
          <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Domain WHOIS & Expiry Checker
          </h2>
          <p className="text-sm text-slate-500 font-medium">
            Enter a domain name to query real-time registration dates, expiration timeline, nameservers, and EPP status flags.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="flex flex-col sm:flex-row items-center gap-3">
            <div className="flex items-center flex-1 w-full bg-slate-50 border border-slate-200/90 rounded-xl px-4 py-3 space-x-3 focus-within:border-slate-400 focus-within:bg-white transition-all">
              <Search className="w-5 h-5 text-slate-400 flex-shrink-0" />
              <input
                type="text"
                value={input}
                onChange={(e) => {
                  setInput(e.target.value);
                  if (validationError) setValidationError('');
                }}
                placeholder="e.g. voidonyx.in or voidpanel.com"
                disabled={isLoading}
                className="w-full bg-transparent text-slate-900 font-mono placeholder-slate-400 focus:outline-none text-sm sm:text-base"
                aria-label="Domain Name Input"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full sm:w-auto px-7 py-3.5 bg-gradient-to-r from-rose-600 to-red-600 hover:from-rose-700 hover:to-red-700 text-white font-bold text-sm rounded-xl shadow-red-glow hover:shadow-lg active:scale-95 transition-all flex items-center justify-center space-x-2 flex-shrink-0 disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Checking WHOIS...</span>
                </>
              ) : (
                <>
                  <ShieldCheck className="w-4 h-4" />
                  <span>Lookup Domain</span>
                </>
              )}
            </button>
          </div>

          <div className="flex items-center justify-between text-xs font-mono pt-1">
            <div className="flex items-center space-x-2">
              <label
                className="flex items-center space-x-1.5 text-slate-500 cursor-pointer hover:text-slate-700 select-none"
                title="Bypass cached WHOIS result and query live registry"
              >
                <input
                  type="checkbox"
                  checked={forceRefresh}
                  onChange={(e) => setForceRefresh(e.target.checked)}
                  className="rounded border-slate-300 text-rose-600 focus:ring-rose-500 cursor-pointer"
                />
                <span>Live Query (Bypass Cache)</span>
              </label>
            </div>
          </div>
        </form>

        {/* Client Validation Error Display */}
        {validationError && (
          <div className="p-3.5 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs font-mono flex items-start space-x-2">
            <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
            <span>{validationError}</span>
          </div>
        )}

        {/* Quick presets chips */}
        <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-100">
          <span className="text-xs text-slate-500 font-medium">Quick presets:</span>
          {PRESET_DOMAINS.map((preset) => (
            <button
              key={preset.value}
              type="button"
              onClick={() => handlePresetClick(preset.value)}
              className="px-3 py-1 text-xs font-mono bg-slate-100 hover:bg-slate-200 border border-slate-200/80 text-slate-700 rounded-lg transition-all"
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
