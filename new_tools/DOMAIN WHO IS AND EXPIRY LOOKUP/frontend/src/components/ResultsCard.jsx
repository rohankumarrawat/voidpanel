import React from 'react';
import {
  Globe,
  Building2,
  Calendar,
  Server,
  Shield,
  Clock,
  Lock,
  CheckCircle,
  Database,
  ExternalLink,
  ShieldCheck,
  AlertCircle
} from 'lucide-react';
import StatusBadge from './StatusBadge';
import DaysRemainingCard from './DaysRemainingCard';
import CollapsibleSection from './CollapsibleSection';
import RawDataViewer from './RawDataViewer';

export default function ResultsCard({ data }) {
  if (!data) return null;

  const {
    domain,
    tld,
    source,
    status,
    isAvailable,
    daysRemaining,
    registrar,
    createdDate,
    expiresDate,
    updatedDate,
    nameServers = [],
    statusFlags = [],
    parsedStatusDetails = [],
    dnssec,
    privacyProtected,
    registrantOrg,
    fromCache,
    cachedAt,
    rawResponse,
  } = data;

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Not Disclosed / Unknown';
    try {
      const d = new Date(dateStr);
      return `${d.toUTCString()} (${d.toLocaleDateString()})`;
    } catch (e) {
      return dateStr;
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6 animate-fadeIn">
      {/* Top Banner Card */}
      <div className="border border-slate-200/90 rounded-[24px] bg-white p-6 sm:p-8 shadow-card space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-100 pb-5">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <span className="px-2.5 py-0.5 rounded-md text-[11px] font-mono bg-slate-100 border border-slate-200 text-slate-700 uppercase tracking-wider font-semibold">
                .{tld} TLD
              </span>
              <span className="px-2.5 py-0.5 rounded-md text-[11px] font-mono bg-slate-100 border border-slate-200 text-slate-600 uppercase tracking-wider flex items-center gap-1">
                <Database className="w-3 h-3 text-rose-600" /> Source: {source?.toUpperCase()}
              </span>
              {fromCache && (
                <span className="px-2.5 py-0.5 rounded-md text-[11px] font-mono bg-amber-50 border border-amber-200 text-amber-800 font-semibold">
                  Cached Result ({cachedAt ? new Date(cachedAt).toLocaleTimeString() : 'Recent'})
                </span>
              )}
            </div>

            <div className="flex items-center space-x-3 pt-2">
              <Globe className="w-7 h-7 text-rose-600" />
              <h2 className="text-2xl sm:text-3xl font-extrabold font-mono text-slate-900 tracking-tight break-all">
                {domain}
              </h2>
            </div>
          </div>

          <div className="self-start md:self-center">
            <StatusBadge status={status} isAvailable={isAvailable} privacyProtected={privacyProtected} />
          </div>
        </div>

        {/* Days Remaining Banner */}
        <DaysRemainingCard daysRemaining={daysRemaining} expiresDate={expiresDate} isAvailable={isAvailable} />
      </div>

      {/* Available / Unregistered Callout */}
      {isAvailable && (
        <div className="border border-blue-200 bg-blue-50/70 rounded-2xl p-6 text-center space-y-3">
          <CheckCircle className="w-8 h-8 text-blue-600 mx-auto" />
          <h3 className="text-lg font-bold text-slate-900">This Domain Does Not Appear To Be Registered</h3>
          <p className="text-sm text-slate-600 max-w-lg mx-auto">
            Our WHOIS & RDAP lookup queries returned no active registration match for <span className="font-mono font-bold text-slate-900">{domain}</span>. This domain is currently available for purchase through domain registrars.
          </p>
        </div>
      )}

      {/* Detail Collapsible Sections */}
      {!isAvailable && (
        <div className="space-y-4">
          {/* 1. Registrar Information */}
          <CollapsibleSection title="Registrar Information" icon={Building2} badge={registrar?.name || 'Registrar'}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm font-mono">
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1">
                <span className="text-xs text-slate-500 block">Registrar Name</span>
                <span className="text-slate-900 font-bold">{registrar?.name || 'Not Disclosed'}</span>
              </div>

              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1">
                <span className="text-xs text-slate-500 block">IANA Registrar ID</span>
                <span className="text-rose-600 font-bold">{registrar?.ianaId ? `#${registrar.ianaId}` : 'Not Specified'}</span>
              </div>

              {registrar?.url && (
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1">
                  <span className="text-xs text-slate-500 block">Registrar Website</span>
                  <a
                    href={registrar.url.startsWith('http') ? registrar.url : `http://${registrar.url}`}
                    target="_blank"
                    rel="noreferrer"
                    className="text-rose-600 font-semibold hover:underline flex items-center space-x-1 break-all"
                  >
                    <span>{registrar.url}</span>
                    <ExternalLink className="w-3.5 h-3.5 flex-shrink-0" />
                  </a>
                </div>
              )}

              {registrar?.email && (
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1">
                  <span className="text-xs text-slate-500 block">Abuse Contact Email</span>
                  <span className="text-slate-800 break-all">{registrar.email}</span>
                </div>
              )}
            </div>
          </CollapsibleSection>

          {/* 2. Lifecycle Dates */}
          <CollapsibleSection title="Registration Dates & Expiry Timeline" icon={Calendar}>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm font-mono">
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1">
                <span className="text-xs text-slate-500 block">Created Date</span>
                <span className="text-emerald-700 font-bold block">{formatDate(createdDate)}</span>
              </div>

              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1">
                <span className="text-xs text-slate-500 block">Expiration Date</span>
                <span className="text-amber-700 font-bold block">{formatDate(expiresDate)}</span>
              </div>

              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1">
                <span className="text-xs text-slate-500 block">Last Updated Date</span>
                <span className="text-slate-900 font-bold block">{formatDate(updatedDate)}</span>
              </div>
            </div>
          </CollapsibleSection>

          {/* 3. Name Servers */}
          <CollapsibleSection title="Authoritative Name Servers" icon={Server} badge={`${nameServers.length} Servers`}>
            {nameServers.length === 0 ? (
              <p className="text-sm font-mono text-slate-500">No name servers returned in record.</p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm font-mono">
                {nameServers.map((ns, idx) => (
                  <div
                    key={idx}
                    className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 text-slate-800 flex items-center space-x-2"
                  >
                    <span className="text-rose-600 text-xs font-bold">0{idx + 1}.</span>
                    <span className="font-semibold text-slate-900 break-all">{ns}</span>
                  </div>
                ))}
              </div>
            )}
          </CollapsibleSection>

          {/* 4. Domain EPP Status Flags with Plain-English Explanations */}
          <CollapsibleSection title="Domain Status Flags (EPP)" icon={Shield} badge={`${statusFlags.length} Flags`}>
            {parsedStatusDetails.length === 0 ? (
              <p className="text-sm font-mono text-slate-500">No EPP status flags associated with domain.</p>
            ) : (
              <div className="space-y-3">
                {parsedStatusDetails.map((flagObj, idx) => (
                  <div key={idx} className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="px-2.5 py-0.5 rounded-md text-[11px] font-mono bg-white border border-slate-200 text-rose-600 font-bold shadow-sm">
                        {flagObj.code}
                      </span>
                    </div>
                    <p className="text-xs text-slate-600 pt-1 leading-relaxed">{flagObj.description}</p>
                  </div>
                ))}
              </div>
            )}
          </CollapsibleSection>

          {/* 5. DNSSEC & Privacy Protection Details */}
          <CollapsibleSection title="Security & Privacy Compliance" icon={ShieldCheck}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm font-mono">
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500 font-medium">DNSSEC Status</span>
                  <span
                    className={`px-2.5 py-0.5 rounded-md text-xs font-bold uppercase ${
                      dnssec === 'signed'
                        ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                        : 'bg-slate-200 text-slate-700 border border-slate-300'
                    }`}
                  >
                    {dnssec}
                  </span>
                </div>
                <p className="text-xs text-slate-600 leading-relaxed">
                  {dnssec === 'signed'
                    ? 'DNSSEC is active and validating cryptographic signatures for domain DNS records.'
                    : 'DNSSEC signatures are not active or not published in root zone.'}
                </p>
              </div>

              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500 font-medium">Registrant Privacy</span>
                  <span
                    className={`px-2.5 py-0.5 rounded-md text-xs font-bold uppercase ${
                      privacyProtected
                        ? 'bg-purple-100 text-purple-800 border border-purple-200'
                        : 'bg-slate-200 text-slate-700 border border-slate-300'
                    }`}
                  >
                    {privacyProtected ? 'Privacy Redacted' : 'Exposed'}
                  </span>
                </div>
                <p className="text-xs text-slate-600 leading-relaxed">
                  {privacyProtected
                    ? 'Registrant details redacted per privacy proxy policy / GDPR regulation.'
                    : registrantOrg
                    ? `Registrant Organization: ${registrantOrg}`
                    : 'Standard ICANN public disclosure.'}
                </p>
              </div>
            </div>
          </CollapsibleSection>
        </div>
      )}

      {/* Raw Data & Copy Options */}
      <RawDataViewer rawData={rawResponse} normalizedData={data} />
    </div>
  );
}
