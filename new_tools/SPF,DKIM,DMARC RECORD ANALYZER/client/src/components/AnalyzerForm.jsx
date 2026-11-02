import React, { useState } from 'react';

export default function AnalyzerForm({ onAnalyze, loading, error }) {
  const [domain, setDomain] = useState('');
  const [selectors, setSelectors] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);

  const presets = [
    { label: 'google.com (Google)', value: 'google.com' },
    { label: 'microsoft.com (MS)', value: 'microsoft.com' },
    { label: 'cloudflare.com', value: 'cloudflare.com' },
    { label: 'yahoo.com', value: 'yahoo.com' },
  ];

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!domain.trim()) return;
    onAnalyze(domain.trim(), selectors.trim());
  };

  const handlePresetClick = (val) => {
    setDomain(val);
    onAnalyze(val, selectors.trim());
  };

  return (
    <div className="hero-card">
      <h1 className="hero-title">SPF, DKIM & DMARC Record Analyzer</h1>
      <p className="hero-description">
        Enter a domain name or host to inspect live SPF lookup limits, DKIM keys, and DMARC enforcement policy.
      </p>

      <form onSubmit={handleSubmit}>
        <div className="search-form-row">
          <div className="input-wrapper">
            <svg className="search-icon" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              className="search-input"
              placeholder="e.g. google.com or mail.yourdomain.com"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              disabled={loading}
            />
          </div>

          <button type="submit" className="btn-analyze" disabled={loading || !domain.trim()}>
            {loading ? (
              <>
                <div className="spinner"></div>
                <span>Analyzing...</span>
              </>
            ) : (
              <>
                <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                <span>Analyze Domain</span>
              </>
            )}
          </button>
        </div>

        {/* Quick Presets */}
        <div className="presets-row">
          <span className="presets-label">Quick presets:</span>
          {presets.map((p, idx) => (
            <button
              key={idx}
              type="button"
              className="preset-chip"
              onClick={() => handlePresetClick(p.value)}
            >
              {p.label}
            </button>
          ))}
          <button
            type="button"
            className="preset-chip"
            style={{ color: 'var(--ox-red-brand)', fontWeight: 600 }}
            onClick={() => setShowAdvanced(!showAdvanced)}
          >
            {showAdvanced ? 'Hide DKIM Selectors' : '+ Add Custom DKIM Selectors'}
          </button>
        </div>

        {/* Advanced Selectors input */}
        {showAdvanced && (
          <div className="selector-input-row">
            <input
              type="text"
              className="selector-input"
              placeholder="Custom DKIM selectors separated by comma (e.g. s1, google, selector1)"
              value={selectors}
              onChange={(e) => setSelectors(e.target.value)}
            />
          </div>
        )}
      </form>

      {error && (
        <div className="alert-item alert-critical" style={{ marginTop: 20 }}>
          <span>⚠️</span>
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
