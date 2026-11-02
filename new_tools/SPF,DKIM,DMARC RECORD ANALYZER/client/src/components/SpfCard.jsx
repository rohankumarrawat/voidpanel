import React, { useState } from 'react';
import LookupTree from './LookupTree';
import { copyToClipboard } from '../utils/clipboard';

export default function SpfCard({ spf }) {
  const [copied, setCopied] = useState(false);

  if (!spf) return null;

  const handleCopy = async () => {
    if (spf.record) {
      const ok = await copyToClipboard(spf.record);
      if (ok) {
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }
    }
  };

  const statusClass = spf.valid ? 'status-pass' : spf.found ? 'status-warn' : 'status-fail';
  const statusLabel = spf.valid ? 'VALID' : spf.found ? 'WARNING' : 'MISSING';

  return (
    <div className="card-box">
      <div className="card-header-row">
        <div className="card-heading">
          <span>1. SPF (Sender Policy Framework)</span>
          <span className={`status-badge-pill ${statusClass}`}>{statusLabel}</span>
        </div>
        <div style={{ fontSize: '0.9rem', fontWeight: 600, color: spf.maxLookupsExceeded ? 'var(--status-fail-text)' : 'var(--text-muted)' }}>
          DNS Lookups: <strong>{spf.lookupCount} / 10</strong> (RFC 7208)
        </div>
      </div>

      {spf.found ? (
        <>
          <div className="raw-code-block">
            <button className="copy-button" onClick={handleCopy}>
              {copied ? 'Copied!' : 'Copy Record'}
            </button>
            {spf.record}
          </div>

          {spf.issues && spf.issues.length > 0 && (
            <div className="issues-container">
              {spf.issues.map((issue, idx) => (
                <div
                  key={idx}
                  className={`alert-item ${
                    issue.startsWith('CRITICAL') || issue.startsWith('RFC') ? 'alert-critical' : 'alert-warning'
                  }`}
                >
                  <span style={{ fontSize: '1.1rem' }}>⚠️</span>
                  <span>{issue}</span>
                </div>
              ))}
            </div>
          )}

          <LookupTree tree={spf.lookupTree} />
        </>
      ) : (
        <div className="alert-item alert-critical">
          <span>🛑</span>
          <span>No published SPF TXT record starting with "v=spf1" was found on the domain apex.</span>
        </div>
      )}
    </div>
  );
}
