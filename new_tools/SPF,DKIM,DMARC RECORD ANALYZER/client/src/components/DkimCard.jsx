import React from 'react';

export default function DkimCard({ dkim }) {
  if (!dkim) return null;

  const foundCount = dkim.foundCount || 0;
  const statusClass = foundCount > 0 ? 'status-pass' : 'status-warn';

  return (
    <div className="card-box">
      <div className="card-header-row">
        <div className="card-heading">
          <span>2. DKIM (DomainKeys Identified Mail)</span>
          <span className={`status-badge-pill ${statusClass}`}>
            {foundCount > 0 ? `${foundCount} SELECTOR(S) FOUND` : 'NO SELECTORS FOUND'}
          </span>
        </div>
      </div>

      <p style={{ fontSize: '0.925rem', color: 'var(--text-muted)', marginBottom: 16 }}>
        Checked {dkim.selectorsChecked?.length || 0} common/custom selector(s): <strong>{(dkim.selectorsChecked || []).join(', ')}</strong>.
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {dkim.results &&
          dkim.results.map((res, idx) => (
            <div key={idx} className="selector-box">
              <div className="selector-header">
                <span className="selector-fqdn">🔑 {res.fqdn}</span>
                <span className={`status-badge-pill ${res.found ? (res.valid ? 'status-pass' : 'status-warn') : 'status-fail'}`}>
                  {res.found ? (res.valid ? 'VALID KEY' : 'REVOKED / INVALID') : 'NOT PUBLISHED'}
                </span>
              </div>

              {res.found && (
                <div className="raw-code-block" style={{ marginTop: 8, fontSize: '0.85rem' }}>
                  {res.record}
                </div>
              )}

              {res.issues &&
                res.issues.map((iss, i) => (
                  <div key={i} className="alert-item alert-warning" style={{ marginTop: 8, fontSize: '0.875rem', padding: '8px 12px' }}>
                    <span>ℹ️</span> <span>{iss}</span>
                  </div>
                ))}
            </div>
          ))}
      </div>
    </div>
  );
}
