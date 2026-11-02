import React, { useState } from 'react';
import { copyToClipboard } from '../utils/clipboard';

export default function DmarcCard({ dmarc, domain }) {
  const [copied, setCopied] = useState(false);

  if (!dmarc) return null;

  const handleCopy = async () => {
    if (dmarc.record) {
      const ok = await copyToClipboard(dmarc.record);
      if (ok) {
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }
    }
  };

  const statusClass = dmarc.found
    ? dmarc.policy === 'reject'
      ? 'status-pass'
      : 'status-warn'
    : 'status-fail';

  return (
    <div className="card-box">
      <div className="card-header-row">
        <div className="card-heading">
          <span>3. DMARC (Domain-based Message Authentication)</span>
          <span className={`status-badge-pill ${statusClass}`}>
            {dmarc.found ? `POLICY: p=${(dmarc.policy || 'none').toUpperCase()}` : 'MISSING'}
          </span>
        </div>
      </div>

      {dmarc.found ? (
        <>
          <div className="raw-code-block">
            <button className="copy-button" onClick={handleCopy}>
              {copied ? 'Copied!' : 'Copy Record'}
            </button>
            {dmarc.record}
          </div>

          <div className="info-grid">
            <div className="info-item">
              <span className="info-label">POLICY ENFORCEMENT</span>
              <span className="info-value" style={{ color: dmarc.policy === 'reject' ? 'var(--status-pass-text)' : 'var(--status-warn-text)' }}>
                p={dmarc.policy} (sp={dmarc.subdomainPolicy || dmarc.policy})
              </span>
            </div>

            <div className="info-item">
              <span className="info-label">ALIGNMENT MODE</span>
              <span className="info-value">
                SPF: {dmarc.alignment?.spf || 'relaxed'} | DKIM: {dmarc.alignment?.dkim || 'relaxed'}
              </span>
            </div>

            <div className="info-item">
              <span className="info-label">AGGREGATE REPORTS (rua)</span>
              <span className="info-value" style={{ fontSize: '0.85rem' }}>
                {dmarc.rua && dmarc.rua.length > 0 ? dmarc.rua.join(', ') : 'None Configured'}
              </span>
            </div>
          </div>

          {dmarc.issues && dmarc.issues.length > 0 && (
            <div className="issues-container">
              {dmarc.issues.map((issue, idx) => (
                <div key={idx} className="alert-item alert-warning">
                  <span>ℹ️</span> <span>{issue}</span>
                </div>
              ))}
            </div>
          )}
        </>
      ) : (
        <div className="alert-item alert-critical">
          <span>🛑</span>
          <span>No DMARC TXT record published at _dmarc.{domain}. Receiving email servers cannot enforce authentication rules on spoofed messages.</span>
        </div>
      )}
    </div>
  );
}
