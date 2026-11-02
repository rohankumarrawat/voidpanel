import React from 'react';
import { AlertTriangle, ShieldAlert, CheckCircle2 } from 'lucide-react';

export default function RiskAssessmentCards({ traceData }) {
  if (!traceData || !traceData.chain) return null;

  const { chain, totalHops, totalTimeMs, securityAudit } = traceData;

  // 1. Latency & Hop Count Assessment
  let latencyRisk = { status: 'PASS', title: 'Optimal Hop Count', detail: `Trace completed cleanly in ${totalHops} hop (${totalTimeMs}ms total latency).` };
  if (totalHops > 3 || totalTimeMs > 800) {
    latencyRisk = {
      status: 'FAIL',
      title: 'High Latency Bottleneck',
      detail: `Exceeds 3 hops (${totalHops} hops, ${totalTimeMs}ms). Adds significant Round-Trip-Time (RTT) delay for users & search crawlers.`
    };
  } else if (totalHops > 2 || totalTimeMs > 400) {
    latencyRisk = {
      status: 'WARN',
      title: 'Multi-Hop Delay Detected',
      detail: `Contains ${totalHops} hops (${totalTimeMs}ms). Recommend collapsing intermediate redirects directly to final target.`
    };
  }

  // 2. Protocol Security Downgrade Check (HTTPS -> HTTP)
  let protocolRisk = { status: 'PASS', title: 'Secure Transport Protocol', detail: 'No unencrypted HTTP downgrades detected across redirect hops.' };
  let hasDowngrade = false;
  for (let i = 0; i < chain.length - 1; i++) {
    if (chain[i].protocol === 'HTTPS' && chain[i + 1].protocol === 'HTTP') {
      hasDowngrade = true;
      break;
    }
  }
  if (hasDowngrade) {
    protocolRisk = {
      status: 'FAIL',
      title: 'Insecure Protocol Downgrade!',
      detail: 'HTTPS request redirected to an unencrypted HTTP intermediate hop. Sensitive tokens or cookies may be intercepted.'
    };
  } else if (chain[0].protocol === 'HTTP' && chain[chain.length - 1].protocol === 'HTTPS') {
    protocolRisk = {
      status: 'PASS',
      title: 'HTTPS Upgrade Enforced',
      detail: 'Initial plain HTTP request cleanly upgraded to HTTPS destination.'
    };
  }

  // 3. SEO Redirect Type Assessment (301/308 vs 302/307)
  let seoRisk = { status: 'PASS', title: 'SEO Link Equity Transfer', detail: 'Permanent redirects (301/308) transfer full PageRank authority.' };
  const tempRedirects = chain.filter(h => h.statusCode === 302 || h.statusCode === 307);
  if (tempRedirects.length > 0) {
    seoRisk = {
      status: 'WARN',
      title: 'Temporary Redirect (302/307) In Use',
      detail: `${tempRedirects.length} hop(s) use temporary status codes (302/307). Search engines may not transfer indexing equity to target URL.`
    };
  }

  // 4. Security Headers Audit Summary
  let securityRisk = { status: 'PASS', title: 'Strong Security Headers', detail: 'All major HTTP security headers configured on target server.' };
  if (securityAudit.summaryCounts.fail > 2) {
    securityRisk = {
      status: 'FAIL',
      title: 'Critical Headers Missing',
      detail: `${securityAudit.summaryCounts.fail} defense headers missing on target response (HSTS, CSP, or Clickjacking protection).`
    };
  } else if (securityAudit.summaryCounts.fail > 0 || securityAudit.summaryCounts.warn > 0) {
    securityRisk = {
      status: 'WARN',
      title: 'Partial Header Coverage',
      detail: `Security grade ${securityAudit.grade} (${securityAudit.score}%). Review remediation code snippets below.`
    };
  }

  const riskItems = [latencyRisk, protocolRisk, seoRisk, securityRisk];

  return (
    <div className="voidonyx-card p-6 md:p-8 my-8">
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6 pb-4 border-b border-slate-200">
        <div>
          <h3 className="text-xl font-extrabold text-slate-900 flex items-center space-x-2">
            <ShieldAlert className="w-5 h-5 text-[#FF5C00]" />
            <span>DevSecOps & SEO Diagnostic Risk Assessment</span>
          </h3>
          <p className="text-xs text-slate-500 mt-1 font-medium">
            Automated analysis of latency penalties, transport protocol security, and search engine indexing equity.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {riskItems.map((item, idx) => (
          <div
            key={idx}
            className={`rounded-2xl p-4 border flex items-start space-x-3 transition-all ${
              item.status === 'PASS'
                ? 'bg-emerald-50/70 border-emerald-200 text-emerald-900'
                : item.status === 'WARN'
                ? 'bg-amber-50/70 border-amber-200 text-amber-900'
                : 'bg-rose-50/70 border-rose-200 text-rose-900'
            }`}
          >
            <div className="p-2 rounded-xl bg-white border border-slate-200 shrink-0 mt-0.5 shadow-sm">
              {item.status === 'PASS' ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              ) : item.status === 'WARN' ? (
                <AlertTriangle className="w-5 h-5 text-amber-600" />
              ) : (
                <ShieldAlert className="w-5 h-5 text-rose-600" />
              )}
            </div>

            <div className="space-y-1">
              <div className="flex items-center space-x-2">
                <h4 className="text-sm font-extrabold text-slate-900">{item.title}</h4>
                <span
                  className={`text-[10px] px-2 py-0.2 font-mono rounded-md font-extrabold uppercase ${
                    item.status === 'PASS'
                      ? 'bg-emerald-100 text-emerald-800'
                      : item.status === 'WARN'
                      ? 'bg-amber-100 text-amber-800'
                      : 'bg-rose-100 text-rose-800'
                  }`}
                >
                  {item.status}
                </span>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed font-sans font-medium">{item.detail}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
