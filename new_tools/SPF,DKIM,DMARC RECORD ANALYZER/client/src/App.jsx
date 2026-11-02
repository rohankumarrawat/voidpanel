import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import AnalyzerForm from './components/AnalyzerForm';
import EmptyState from './components/EmptyState';
import OverallScore from './components/OverallScore';
import SpfCard from './components/SpfCard';
import DkimCard from './components/DkimCard';
import DmarcCard from './components/DmarcCard';
import ScanHistory from './components/ScanHistory';
import { analyzeDomain, fetchScanHistory } from './services/api';

export default function App() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [globalHistory, setGlobalHistory] = useState([]);
  const [myLogs, setMyLogs] = useState(() => {
    try {
      const saved = sessionStorage.getItem('my_audit_logs');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });
  const [activeTab, setActiveTab] = useState('analyzer');

  const loadHistory = async () => {
    try {
      const scans = await fetchScanHistory();
      setGlobalHistory(scans);
    } catch (err) {
      console.warn('Global scan history load warning:', err.message);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const handleAnalyze = async (domain, selectors) => {
    setError('');
    setLoading(true);
    setResult(null);

    try {
      const data = await analyzeDomain(domain, selectors);
      setResult(data);

      setMyLogs((prev) => {
        const filteredPrev = prev.filter((s) => s.timestamp !== data.timestamp && s.domain !== data.domain);
        const updated = [data, ...filteredPrev];
        try {
          sessionStorage.setItem('my_audit_logs', JSON.stringify(updated.slice(0, 50)));
        } catch {}
        return updated;
      });

      loadHistory();
    } catch (err) {
      setError(err.message || 'An error occurred during analysis.');
    } finally {
      setLoading(false);
    }
  };

  const handleClearMyLogs = () => {
    setMyLogs([]);
    try {
      sessionStorage.removeItem('my_audit_logs');
    } catch {}
  };

  const handleSelectHistoryScan = (scan) => {
    setResult(scan);
    setActiveTab('analyzer');
  };

  return (
    <div>
      {/* Top Navbar */}
      <Header />

      {/* Main Layout Container */}
      <main className="main-layout">
        {/* Tabs Navigation */}
        <div className="tabs-nav">
          <button
            className={`tab-button ${activeTab === 'analyzer' ? 'active' : ''}`}
            onClick={() => setActiveTab('analyzer')}
          >
            🔍 Record Analyzer
          </button>
          <button
            className={`tab-button ${activeTab === 'history' ? 'active' : ''}`}
            onClick={() => setActiveTab('history')}
          >
            📜 Audit Logs ({myLogs.length} My | {globalHistory.length} Global)
          </button>
        </div>

        {activeTab === 'analyzer' && (
          <>
            <AnalyzerForm onAnalyze={handleAnalyze} loading={loading} error={error} />

            {result ? (
              <div className="results-container">
                <OverallScore
                  domain={result.domain}
                  score={result.overallScore}
                  timestamp={result.timestamp}
                />

                <div className="cards-grid-layout">
                  <SpfCard spf={result.spf} />
                  <DkimCard dkim={result.dkim} />
                  <DmarcCard dmarc={result.dmarc} domain={result.domain} />
                </div>
              </div>
            ) : (
              !loading && <EmptyState />
            )}
          </>
        )}

        {activeTab === 'history' && (
          <ScanHistory
            myLogs={myLogs}
            globalLogs={globalHistory}
            onSelectDomain={handleSelectHistoryScan}
            onClearMyLogs={handleClearMyLogs}
            onRefreshGlobalLogs={loadHistory}
          />
        )}
      </main>
    </div>
  );
}
