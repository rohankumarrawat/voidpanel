import React, { useState, useEffect } from 'react';
import { Search, Shield, AlertCircle, RefreshCw } from 'lucide-react';

const SUGGESTIONS = [
  { label: '1.1.1.1 (Cloudflare)', host: '1.1.1.1', port: 443 },
  { label: '8.8.8.8 (Google)', host: '8.8.8.8', port: 443 },
  { label: 'google.com', host: 'google.com', port: 443 },
  { label: 'voidonyx.in', host: 'voidonyx.in', port: 443 },
  { label: 'expired.badssl.com', host: 'expired.badssl.com', port: 443 },
];

export default function SearchForm({ onSearch, isLoading, initialHost = '', initialPort = 443 }) {
  const [hostInput, setHostInput] = useState(initialHost);
  const [portInput, setPortInput] = useState(initialPort);
  const [validationError, setValidationError] = useState('');
  const [loadingStep, setLoadingStep] = useState(0);

  const steps = [
    'Connecting via TCP socket...',
    'Exchanging ClientHello & SNI header...',
    'Extracting SSL/TLS certificate & SANs...',
    'Validating trust chain & protocol versions...',
    'Finalizing security analysis...',
  ];

  useEffect(() => {
    let interval;
    if (isLoading) {
      setLoadingStep(0);
      interval = setInterval(() => {
        setLoadingStep((prev) => (prev < steps.length - 1 ? prev + 1 : prev));
      }, 700);
    }
    return () => clearInterval(interval);
  }, [isLoading]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!hostInput.trim()) {
      setValidationError('Please enter a target host or domain name.');
      return;
    }
    setValidationError('');
    onSearch(hostInput.trim(), portInput);
  };

  const handleSuggestionClick = (sugHost, sugPort) => {
    setHostInput(sugHost);
    setPortInput(sugPort);
    setValidationError('');
    onSearch(sugHost, sugPort);
  };

  return (
    <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200/90 shadow-sm space-y-6">
      
      {/* Title & Description */}
      <div className="space-y-1">
        <h2 className="text-2xl font-extrabold text-slate-900 tracking-tight">
          SSL/TLS Certificate Expiry Checker
        </h2>
        <p className="text-sm text-slate-500">
          Enter an IPv4 address or domain name to inspect SSL/TLS certificates, expiration dates, trust chains, and protocols.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="flex flex-col sm:flex-row gap-3 items-stretch">
          
          {/* Domain / IP Field */}
          <div className="relative flex-1">
            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400">
              <Search className="w-5 h-5" />
            </div>
            <input
              type="text"
              value={hostInput}
              onChange={(e) => {
                setHostInput(e.target.value);
                if (validationError) setValidationError('');
              }}
              placeholder="e.g. 192.0.2.1 or mail.yourdomain.com"
              disabled={isLoading}
              className="w-full pl-11 pr-4 py-3.5 bg-slate-50 border border-slate-200/90 rounded-full text-slate-900 placeholder-slate-400 text-sm font-medium focus:outline-none focus:bg-white focus:border-red-500 focus:ring-4 focus:ring-red-500/10 transition-all disabled:opacity-60"
            />
          </div>

          {/* Port Field */}
          <div className="w-full sm:w-28">
            <input
              type="number"
              value={portInput}
              onChange={(e) => setPortInput(e.target.value)}
              placeholder="Port"
              min="1"
              max="65535"
              disabled={isLoading}
              className="w-full px-4 py-3.5 bg-slate-50 border border-slate-200/90 rounded-full text-slate-900 placeholder-slate-400 text-sm font-medium text-center focus:outline-none focus:bg-white focus:border-red-500 focus:ring-4 focus:ring-red-500/10 transition-all disabled:opacity-60"
            />
          </div>

          {/* Red Pill Submit Button */}
          <button
            type="submit"
            disabled={isLoading}
            className="px-7 py-3.5 bg-red-600 hover:bg-red-700 active:bg-red-800 text-white font-semibold text-sm rounded-full flex items-center justify-center gap-2 transition-all shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
          >
            {isLoading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Checking...</span>
              </>
            ) : (
              <>
                <Shield className="w-4 h-4 fill-white/20" />
                <span>Check Certificate</span>
              </>
            )}
          </button>
        </div>

        {/* Validation Error Message */}
        {validationError && (
          <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-2xl text-xs font-medium text-red-600">
            <AlertCircle className="w-4 h-4 shrink-0 text-red-500" />
            <span>{validationError}</span>
          </div>
        )}

        {/* Quick Presets Pills */}
        <div className="pt-1 flex flex-wrap items-center gap-2 text-xs">
          <span className="text-slate-400 font-medium mr-1">Quick presets:</span>
          {SUGGESTIONS.map((sug) => (
            <button
              key={sug.label}
              type="button"
              onClick={() => handleSuggestionClick(sug.host, sug.port)}
              disabled={isLoading}
              className="px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200/80 text-slate-700 font-medium transition-all"
            >
              {sug.label}
            </button>
          ))}
        </div>
      </form>

      {/* Loading Progress Bar */}
      {isLoading && (
        <div className="p-4 rounded-2xl bg-red-50/60 border border-red-100 text-xs text-red-700 space-y-2 animate-pulse">
          <div className="flex items-center justify-between font-semibold">
            <span className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-ping"></span>
              Live Handshake Engine
            </span>
            <span>Target: {hostInput}:{portInput}</span>
          </div>
          <div className="font-medium text-slate-600">
            &gt; {steps[loadingStep]}
          </div>
        </div>
      )}
    </div>
  );
}

