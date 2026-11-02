import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import TraceInput from './components/TraceInput';
import SummaryCards from './components/SummaryCards';
import RedirectFlowDiagram from './components/RedirectFlowDiagram';
import RiskAssessmentCards from './components/RiskAssessmentCards';
import RedirectChainView from './components/RedirectChainView';
import SecurityHeaderAudit from './components/SecurityHeaderAudit';
import HeaderInspectorTable from './components/HeaderInspectorTable';
import HeaderDiffModal from './components/HeaderDiffModal';
import CurlGeneratorModal from './components/CurlGeneratorModal';
import TraceHistoryDrawer from './components/TraceHistoryDrawer';
import VoidPanelLogo from './components/VoidPanelLogo';
import { GitCompare, Terminal, ShieldCheck } from 'lucide-react';

export default function App() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [traceData, setTraceData] = useState(null);
  const [selectedHop, setSelectedHop] = useState(null);

  // Modals state
  const [isDiffOpen, setIsDiffOpen] = useState(false);
  const [isCurlOpen, setIsCurlOpen] = useState(false);
  const [curlHopTarget, setCurlHopTarget] = useState(null);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

  // History state from localStorage
  const [history, setHistory] = useState([]);

  useEffect(() => {
    try {
      const saved = localStorage.getItem('tracer_history');
      if (saved) {
        setHistory(JSON.parse(saved));
      }
    } catch (e) {
      console.error('Failed to parse tracer history:', e);
    }
  }, []);

  const saveHistory = (url, resData) => {
    try {
      const finalHop = resData.chain ? resData.chain[resData.chain.length - 1] : null;
      const newItem = {
        url,
        hops: resData.totalHops,
        finalStatus: finalHop ? `${finalHop.statusCode} ${finalHop.statusText}` : '200 OK',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      const filtered = history.filter(h => h.url.toLowerCase() !== url.toLowerCase());
      const updated = [newItem, ...filtered].slice(0, 15);
      setHistory(updated);
      localStorage.setItem('tracer_history', JSON.stringify(updated));
    } catch (e) {
      console.error('Failed to save tracer history:', e);
    }
  };

  const handleClearHistory = () => {
    setHistory([]);
    localStorage.removeItem('tracer_history');
  };

  const handleTrace = async (targetUrl, userAgent) => {
    setLoading(true);
    setError('');
    setTraceData(null);
    setSelectedHop(null);

    try {
      const response = await fetch('/api/trace', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ url: targetUrl, userAgent })
      });

      const resData = await response.json();

      if (!response.ok || !resData.success) {
        throw new Error(resData.error || 'Failed to complete redirect trace.');
      }

      setTraceData(resData.data);
      if (resData.data.chain && resData.data.chain.length > 0) {
        setSelectedHop(resData.data.chain[resData.data.chain.length - 1]);
      }

      saveHistory(targetUrl, resData.data);
    } catch (err) {
      setError(err.message || 'An unexpected error occurred.');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectHistoryItem = async (item) => {
    const targetUrl = typeof item === 'string' ? item : item.url;
    const itemId = typeof item === 'object' ? item.id : null;

    if (itemId) {
      setLoading(true);
      setError('');
      try {
        const response = await fetch(`/api/history/${itemId}`);
        const resData = await response.json();
        if (response.ok && resData.success && resData.data && resData.data.chain) {
          setTraceData(resData.data);
          if (resData.data.chain.length > 0) {
            setSelectedHop(resData.data.chain[resData.data.chain.length - 1]);
          }
          setLoading(false);
          return;
        }
      } catch (e) {
        console.warn('Failed to fetch trace by ID from MongoDB, running fresh trace:', e);
      }
    }

    if (targetUrl) {
      handleTrace(targetUrl);
    }
  };

  const openCurlModalForHop = (hop) => {
    setCurlHopTarget(hop);
    setIsCurlOpen(true);
  };

  return (
    <div className="min-h-screen bg-[#FAF8F5] text-slate-900 flex flex-col font-sans">
      <Navbar
        onOpenDiff={() => setIsDiffOpen(true)}
        onOpenCurl={(hop) => openCurlModalForHop(hop)}
        onOpenHistory={() => setIsHistoryOpen(true)}
        traceData={traceData}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <TraceInput
          onTrace={handleTrace}
          loading={loading}
          error={error}
          onOpenHistory={() => setIsHistoryOpen(true)}
        />

        {traceData && (
          <div className="space-y-8 animate-fadeIn">
            {/* Active Trace Control Bar */}
            <div className="flex flex-wrap items-center justify-between gap-3 p-4 bg-white rounded-2xl border border-slate-200 shadow-sm text-xs">
              <div className="flex items-center space-x-2.5">
                <span className="w-2.5 h-2.5 rounded-full bg-[#E11D48] animate-ping" />
                <span className="font-extrabold text-slate-900">Active Trace Target:</span>
                <span className="font-mono text-[#E11D48] font-bold truncate max-w-xs sm:max-w-md">{traceData.inputUrl}</span>
              </div>

              <div className="flex items-center space-x-2">
                <button
                  type="button"
                  onClick={() => setIsDiffOpen(true)}
                  className="px-3 py-1.5 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl font-bold text-purple-700 flex items-center space-x-1.5 transition-all shadow-xs"
                >
                  <GitCompare className="w-3.5 h-3.5" />
                  <span>Diff Hops</span>
                </button>

                <button
                  type="button"
                  onClick={() => openCurlModalForHop(null)}
                  className="px-3 py-1.5 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl font-bold text-rose-600 flex items-center space-x-1.5 transition-all shadow-xs"
                >
                  <Terminal className="w-3.5 h-3.5" />
                  <span>cURL Script</span>
                </button>
              </div>
            </div>

            {/* Summary KPI Cards & Latency Breakdown */}
            <SummaryCards data={traceData} />

            {/* Interactive Visual Node Diagram */}
            <RedirectFlowDiagram
              chain={traceData.chain}
              selectedHop={selectedHop}
              onSelectHop={(hop) => setSelectedHop(hop)}
            />

            {/* DevSecOps & SEO Risk Assessment */}
            <RiskAssessmentCards traceData={traceData} />

            {/* Step-by-Step Redirect Chain Timeline */}
            <RedirectChainView
              chain={traceData.chain}
              onSelectHopHeaders={(hop) => setSelectedHop(hop)}
            />

            {/* Security Header Audit & Fix Snippets */}
            <SecurityHeaderAudit audit={traceData.securityAudit} />

            {/* Raw HTTP Response Headers Table */}
            <HeaderInspectorTable hop={selectedHop} fullResult={traceData} />
          </div>
        )}

        {/* Empty State Card matching tools.voidonyx.in */}
        {!traceData && !loading && !error && (
          <div className="max-w-5xl mx-auto my-12 bg-white rounded-3xl p-12 md:p-16 border border-slate-200/90 shadow-xl shadow-slate-200/50 text-center space-y-4">
            <div className="w-16 h-16 rounded-2xl bg-rose-50 border border-rose-100 flex items-center justify-center mx-auto text-[#E11D48] shadow-xs">
              <ShieldCheck className="w-8 h-8 stroke-[2.2]" />
            </div>
            <h2 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Ready to Trace Redirect Chains
            </h2>
            <p className="text-sm text-slate-500 max-w-xl mx-auto leading-relaxed font-medium">
              Enter any IPv4 address, domain or URL above to instantly trace HTTP status codes, latency breakdown & security headers in real-time.
            </p>
          </div>
        )}
      </main>

      {/* Modals & Slide-over Drawers */}
      <HeaderDiffModal
        isOpen={isDiffOpen}
        onClose={() => setIsDiffOpen(false)}
        chain={traceData ? traceData.chain : []}
      />

      <CurlGeneratorModal
        isOpen={isCurlOpen}
        onClose={() => setIsCurlOpen(false)}
        traceData={traceData}
        hop={curlHopTarget}
      />

      <TraceHistoryDrawer
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        history={history}
        onSelectHistory={handleSelectHistoryItem}
        onClearHistory={handleClearHistory}
      />

      <footer className="border-t border-slate-200 bg-white py-8 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center space-x-2">
            <VoidPanelLogo showSubtitle={false} />
            <span className="text-slate-400 font-semibold">| VoidOnyx Tools Engine</span>
          </div>

          <span className="text-slate-500 font-medium">
            © 2026 VoidOnyx Tools. All rights reserved.
          </span>
        </div>
      </footer>
    </div>
  );
}
