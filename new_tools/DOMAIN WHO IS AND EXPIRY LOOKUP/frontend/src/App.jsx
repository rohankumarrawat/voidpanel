import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Header from './components/Header';
import DomainInput from './components/DomainInput';
import ResultsCard from './components/ResultsCard';
import RecentSearches from './components/RecentSearches';
import Footer from './components/Footer';
import {
  Shield,
  Clock,
  Server,
  AlertTriangle,
  Activity,
  ShieldCheck
} from 'lucide-react';

// Helper to generate or retrieve browser session ID for browser-isolated history
const getOrCreateSessionId = () => {
  let sid = localStorage.getItem('voidonyx_session_id');
  if (!sid) {
    sid = 'sess_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9);
    localStorage.setItem('voidonyx_session_id', sid);
  }
  return sid;
};

// Local storage personal history helper (isolated per browser/profile)
const getLocalPersonalHistory = () => {
  try {
    const raw = localStorage.getItem('voidonyx_personal_history');
    return raw ? JSON.parse(raw) : [];
  } catch (e) {
    return [];
  }
};

const saveToLocalPersonalHistory = (item) => {
  try {
    const current = getLocalPersonalHistory();
    const filtered = current.filter((x) => x.domain.toLowerCase() !== item.domain.toLowerCase());
    const updated = [item, ...filtered].slice(0, 10);
    localStorage.setItem('voidonyx_personal_history', JSON.stringify(updated));
    return updated;
  } catch (e) {
    return [];
  }
};

export default function App() {
  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [myHistory, setMyHistory] = useState(getLocalPersonalHistory);
  const [globalHistory, setGlobalHistory] = useState([]);
  const [currentDomain, setCurrentDomain] = useState('');
  const [sessionId] = useState(getOrCreateSessionId);

  const fetchHistory = async () => {
    const localPersonal = getLocalPersonalHistory();
    setMyHistory(localPersonal);

    try {
      const [myRes, globalRes] = await Promise.all([
        axios.get('/api/whois/history?type=my&limit=8', {
          headers: { 'X-Session-ID': sessionId },
        }),
        axios.get('/api/whois/history?type=global&limit=8'),
      ]);

      if (myRes.data && myRes.data.success && Array.isArray(myRes.data.data)) {
        // Filter server responses so items belonging to another session are discarded
        const serverFiltered = myRes.data.data.filter(
          (item) => item.sessionId === sessionId
        );

        const map = new Map();
        [...localPersonal, ...serverFiltered].forEach((item) => {
          if (item && item.domain) {
            map.set(item.domain.toLowerCase(), item);
          }
        });
        setMyHistory(Array.from(map.values()));
      }

      if (globalRes.data && globalRes.data.success) {
        setGlobalHistory(globalRes.data.data);
      }
    } catch (err) {
      // Ignore silent history fetch error
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [sessionId]);

  const handleSearch = async (domain, forceRefresh = false) => {
    setIsLoading(true);
    setError('');
    setResult(null);
    setCurrentDomain(domain);

    try {
      const response = await axios.post(
        '/api/whois/lookup',
        {
          domain,
          forceRefresh,
        },
        {
          headers: { 'X-Session-ID': sessionId },
        }
      );

      if (response.data && response.data.success) {
        const lookupResult = response.data.data;
        setResult(lookupResult);

        // Save to browser-isolated local history
        saveToLocalPersonalHistory({
          domain: lookupResult.domain,
          tld: lookupResult.tld,
          status: lookupResult.status,
          daysRemaining: lookupResult.daysRemaining,
          checkedAt: new Date().toISOString(),
        });

        fetchHistory();
      } else {
        setError(response.data?.error || 'Failed to retrieve WHOIS data.');
      }
    } catch (err) {
      if (err.response && err.response.data && err.response.data.error) {
        setError(err.response.data.error);
      } else {
        setError(
          `Unable to connect to WHOIS lookup API service. Please verify your connection or retry in a few moments.`
        );
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearMyHistory = () => {
    try {
      localStorage.removeItem('voidonyx_personal_history');
    } catch (e) {}
    setMyHistory([]);
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 font-sans">
      <Header />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-10">
        {/* Main Form Box */}
        <DomainInput onSearch={handleSearch} isLoading={isLoading} initialValue={currentDomain} />

        {/* Loading Scanner */}
        {isLoading && (
          <div className="max-w-4xl mx-auto p-10 rounded-[24px] bg-white border border-rose-200 text-center space-y-4 shadow-card animate-pulse">
            <div className="w-14 h-14 rounded-full bg-rose-50 border-2 border-rose-500 flex items-center justify-center mx-auto text-rose-600 shadow-sm">
              <Activity className="w-7 h-7 animate-spin" />
            </div>
            <div className="space-y-1">
              <p className="font-mono text-base font-bold text-slate-900">Resolving IANA Referral & Querying Authority...</p>
              <p className="font-mono text-xs text-rose-600 font-semibold">Connecting to TCP Port 43 Socket / HTTPS RDAP Registry</p>
            </div>
          </div>
        )}

        {/* Error Display Card */}
        {error && !isLoading && (
          <div className="max-w-4xl mx-auto p-6 rounded-2xl bg-red-50 border border-red-200 text-red-900 space-y-3 shadow-sm">
            <div className="flex items-center space-x-3">
              <AlertTriangle className="w-6 h-6 text-red-600 flex-shrink-0" />
              <h3 className="text-base font-bold font-mono text-slate-900">WHOIS Lookup Error</h3>
            </div>
            <p className="text-xs font-mono leading-relaxed pl-9 text-red-700">{error}</p>
          </div>
        )}

        {/* Results Card */}
        {!isLoading && result && <ResultsCard data={result} />}

        {/* Default / First-Load Card matching screenshot icon badge */}
        {!isLoading && !result && !error && (
          <div className="w-full max-w-4xl mx-auto">
            <div className="bg-white border border-slate-200/90 rounded-[24px] p-8 sm:p-12 text-center shadow-card space-y-6">
              <div className="w-16 h-16 rounded-2xl bg-rose-50 border border-rose-100 flex items-center justify-center mx-auto text-rose-600 shadow-sm">
                <ShieldCheck className="w-8 h-8" />
              </div>

              <div className="space-y-2 max-w-lg mx-auto">
                <h3 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
                  Ready to Query WHOIS & Expiry Data
                </h3>
                <p className="text-sm text-slate-500 font-medium leading-relaxed">
                  Enter any domain name above to instantly check its registration dates, expiration timeline, nameservers, EPP status flags, and DNSSEC signatures.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4 border-t border-slate-100 max-w-3xl mx-auto text-left font-mono">
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1">
                  <div className="flex items-center space-x-2 text-rose-600 font-bold text-xs">
                    <Server className="w-4 h-4" />
                    <span>IANA Referral</span>
                  </div>
                  <p className="text-[11px] text-slate-500 font-sans leading-relaxed">
                    Auto-resolves authoritative WHOIS & RDAP registry endpoints for all TLDs.
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1">
                  <div className="flex items-center space-x-2 text-amber-600 font-bold text-xs">
                    <Clock className="w-4 h-4" />
                    <span>Expiry Monitor</span>
                  </div>
                  <p className="text-[11px] text-slate-500 font-sans leading-relaxed">
                    Calculates exact days remaining before expiration to prevent domain drops.
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1">
                  <div className="flex items-center space-x-2 text-purple-600 font-bold text-xs">
                    <Shield className="w-4 h-4" />
                    <span>EPP & GDPR</span>
                  </div>
                  <p className="text-[11px] text-slate-500 font-sans leading-relaxed">
                    Translates ICANN EPP status codes and identifies GDPR privacy redactions.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Dual-Column History & Global Feed */}
        <RecentSearches
          myHistory={myHistory}
          globalHistory={globalHistory}
          onSelectDomain={(d) => handleSearch(d, false)}
          onClearMyHistory={handleClearMyHistory}
        />
      </main>

      <Footer />
    </div>
  );
}
