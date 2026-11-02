import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import SearchForm from './components/SearchForm';
import StatusBanner from './components/StatusBanner';
import CollapsibleSection from './components/CollapsibleSection';
import CertDetails from './components/CertDetails';
import SansList from './components/SansList';
import IssuerChain from './components/IssuerChain';
import ProtocolSupport from './components/ProtocolSupport';
import RecentChecks from './components/RecentChecks';
import Footer from './components/Footer';
import { checkCertificate, fetchRecentChecks } from './utils/api';
import { FileText, Globe, Layers, Lock, AlertTriangle, ShieldCheck as ShieldIcon } from 'lucide-react';

export default function App() {
  const [activeResult, setActiveResult] = useState(null);
  const [errorResult, setErrorResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [recentChecks, setRecentChecks] = useState([]);
  const [currentHost, setCurrentHost] = useState('');
  const [currentPort, setCurrentPort] = useState(443);

  // Initial load: Fetch recent public checks & load default example
  useEffect(() => {
    loadRecentFeed();
  }, []);

  const loadRecentFeed = async () => {
    const feed = await fetchRecentChecks();
    setRecentChecks(feed);
  };

  const handleInspect = async (host, port = 443) => {
    setIsLoading(true);
    setErrorResult(null);
    setCurrentHost(host);
    setCurrentPort(port);

    const res = await checkCertificate(host, port);
    setIsLoading(false);

    if (res.success) {
      setActiveResult(res.data);
      loadRecentFeed(); // Refresh live feed
    } else {
      setActiveResult(null);
      setErrorResult(res);
    }
  };

  return (
    <div className="min-h-screen flex flex-col justify-between bg-slate-50 text-slate-900">
      <div>
        <Header />

        <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
          
          {/* Main Inspection Form */}
          <SearchForm
            onSearch={handleInspect}
            isLoading={isLoading}
            initialHost={currentHost}
            initialPort={currentPort}
          />

          {/* Error / Rate Limit / Handshake Failure Alert */}
          {errorResult && (
            <div className="bg-red-50 rounded-2xl p-6 border border-red-200 text-red-900 space-y-2 shadow-sm">
              <div className="flex items-center gap-3 text-red-700 font-bold text-sm">
                <AlertTriangle className="w-5 h-5 shrink-0 text-red-600" />
                <span>{errorResult.error || 'Inspection Failed'} ({errorResult.code})</span>
              </div>
              <p className="text-xs text-red-700">
                {errorResult.message}
              </p>
              {errorResult.resetInSeconds && (
                <div className="text-xs font-semibold text-amber-700">
                  Rate limit resets in {errorResult.resetInSeconds} second(s).
                </div>
              )}
            </div>
          )}

          {/* Active Result Panels */}
          {activeResult && !isLoading && (
            <div className="space-y-6 animate-fadeIn">
              
              {/* Prominent Status Banner & Days Counter */}
              <StatusBanner data={activeResult} />

              {/* Collapsible Section 1: Certificate & Key Properties */}
              <CollapsibleSection
                title="Certificate Details & Cryptography"
                icon={FileText}
                defaultOpen={true}
              >
                <CertDetails data={activeResult} />
              </CollapsibleSection>

              {/* Collapsible Section 2: Subject Alternative Names (SANs) */}
              <CollapsibleSection
                title="Subject Alternative Names (SANs)"
                icon={Globe}
                badge={activeResult.sans?.length || 0}
                defaultOpen={true}
              >
                <SansList sans={activeResult.sans} targetHost={activeResult.host} />
              </CollapsibleSection>

              {/* Collapsible Section 3: Issuer Chain & Hierarchy */}
              <CollapsibleSection
                title="Issuer Chain & CA Hierarchy"
                icon={Layers}
                badge={`${activeResult.chainDepth || 1} Tier(s)`}
                defaultOpen={true}
              >
                <IssuerChain certChain={activeResult.certChain} chainDepth={activeResult.chainDepth} />
              </CollapsibleSection>

              {/* Collapsible Section 4: Protocol & Security Support */}
              <CollapsibleSection
                title="Protocol & Security Capabilities"
                icon={Lock}
                defaultOpen={true}
              >
                <ProtocolSupport
                  protocol={activeResult.protocol}
                  tlsVersionsSupported={activeResult.tlsVersionsSupported}
                  publicKey={activeResult.publicKey}
                />
              </CollapsibleSection>
            </div>
          )}

          {/* Initial State Card */}
          {!activeResult && !errorResult && !isLoading && (
            <div className="bg-white rounded-3xl p-12 border border-slate-200/90 shadow-sm text-center flex flex-col items-center justify-center space-y-4">
              <div className="w-16 h-16 rounded-2xl bg-red-50 text-red-600 flex items-center justify-center border border-red-100 shadow-inner">
                <ShieldIcon className="w-8 h-8 stroke-[2.2]" />
              </div>
              <h3 className="text-2xl font-extrabold text-slate-900 tracking-tight">
                Ready to Scan Certificate
              </h3>
              <p className="text-sm text-slate-500 max-w-md">
                Enter an IPv4 address or domain name above to scan SSL/TLS certificates in parallel.
              </p>
            </div>
          )}

          {/* Live Activity Feed Ticker */}
          <RecentChecks recentChecks={recentChecks} onSelectHost={handleInspect} />
        </main>
      </div>

      <Footer />
    </div>
  );
}
