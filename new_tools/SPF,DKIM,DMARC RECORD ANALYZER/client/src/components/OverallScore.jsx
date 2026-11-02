import React from 'react';

export default function OverallScore({ domain, score, timestamp }) {
  const scoreClass = score ? `score-${score.replace(/\s+/g, '-')}` : 'score-Needs-Improvement';

  return (
    <div className="score-summary-bar">
      <div>
        <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', fontWeight: 700, letterSpacing: '0.05em', marginBottom: 4 }}>
          ANALYSIS POSTURE REPORT • {new Date(timestamp).toLocaleString()}
        </div>
        <div className="domain-name">{domain}</div>
      </div>

      <div className={`badge-score ${scoreClass}`}>
        Overall Score: {score}
      </div>
    </div>
  );
}
