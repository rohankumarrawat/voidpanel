import React, { useState } from 'react';

export default function ScanHistory({
  myLogs = [],
  globalLogs = [],
  onSelectDomain,
  onClearMyLogs,
  onRefreshGlobalLogs,
}) {
  const [mySearch, setMySearch] = useState('');
  const [globalSearch, setGlobalSearch] = useState('');

  const filteredMyLogs = myLogs.filter((scan) =>
    scan.domain.toLowerCase().includes(mySearch.toLowerCase().trim())
  );

  const filteredGlobalLogs = globalLogs.filter((scan) =>
    scan.domain.toLowerCase().includes(globalSearch.toLowerCase().trim())
  );

  const renderTable = (logs, emptyMessage) => {
    if (!logs || logs.length === 0) {
      return <p className="empty-log-text">{emptyMessage}</p>;
    }

    return (
      <div className="table-container">
        <table className="history-table">
          <thead>
            <tr>
              <th>Domain</th>
              <th>Score</th>
              <th>SPF / DMARC</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((scan, idx) => {
              const scoreClass = scan.overallScore
                ? `score-${scan.overallScore.replace(/\s+/g, '-')}`
                : 'score-Needs-Improvement';

              const timeStr = scan.timestamp
                ? new Date(scan.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                : 'Recent';

              return (
                <tr key={scan._id || idx}>
                  <td>
                    <button
                      className="history-domain-btn"
                      onClick={() => onSelectDomain(scan)}
                      title={`Inspect ${scan.domain}`}
                    >
                      {scan.domain}
                    </button>
                  </td>
                  <td>
                    <span className={`status-badge-pill ${scoreClass}`}>
                      {scan.overallScore || 'Unknown'}
                    </span>
                  </td>
                  <td className="status-compact">
                    <span className="status-item">{scan.spf?.valid ? '✅ SPF' : '⚠️ SPF'}</span>
                    <span className="dot-sep">•</span>
                    <span className="status-item">{scan.dmarc?.policy ? `p=${scan.dmarc.policy}` : '❌ DMARC'}</span>
                  </td>
                  <td className="timestamp-cell">{timeStr}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div className="audit-logs-section">
      <div className="audit-logs-header">
        <h2 className="table-title">Domain Audit Log Registry</h2>
        <p className="audit-logs-subtitle">
          Separate views for your personal session audit logs and global system-wide DNS audit logs.
        </p>
      </div>

      <div className="audit-logs-grid">
        {/* Left Column: My Audit Logs */}
        <div className="audit-column-card">
          <div className="audit-column-header">
            <div className="title-group">
              <h3 className="audit-column-title">
                👤 My Audit Logs
                <span className="audit-count-badge">{myLogs.length}</span>
              </h3>
            </div>
            {myLogs.length > 0 && (
              <button className="btn-clear-logs" onClick={onClearMyLogs} title="Clear session history">
                Clear My Logs
              </button>
            )}
          </div>

          <input
            type="text"
            className="audit-search-input"
            placeholder="🔍 Filter my audit logs..."
            value={mySearch}
            onChange={(e) => setMySearch(e.target.value)}
          />

          {renderTable(
            filteredMyLogs,
            mySearch ? `No session logs match "${mySearch}".` : 'No session scans yet. Run a domain analysis above to view your audit logs here.'
          )}
        </div>

        {/* Right Column: Global Audit Logs */}
        <div className="audit-column-card">
          <div className="audit-column-header">
            <div className="title-group">
              <h3 className="audit-column-title">
                🌐 Global Audit Logs
                <span className="audit-count-badge">{globalLogs.length}</span>
              </h3>
            </div>
            {onRefreshGlobalLogs && (
              <button className="btn-refresh-logs" onClick={onRefreshGlobalLogs} title="Refresh system audit logs">
                🔄 Refresh
              </button>
            )}
          </div>

          <input
            type="text"
            className="audit-search-input"
            placeholder="🔍 Search global system logs..."
            value={globalSearch}
            onChange={(e) => setGlobalSearch(e.target.value)}
          />

          {renderTable(
            filteredGlobalLogs,
            globalSearch ? `No global logs match "${globalSearch}".` : 'No system-wide audit logs found in database.'
          )}
        </div>
      </div>
    </div>
  );
}
