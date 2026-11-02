/**
 * Security Header Analyzer
 * Evaluates key HTTP security headers and generates audit results, grades, and remediation guidance.
 */

function analyzeHeaders(headers, protocol = 'https:') {
  const normalized = {};
  for (const [key, value] of Object.entries(headers || {})) {
    normalized[key.toLowerCase()] = Array.isArray(value) ? value.join(', ') : String(value);
  }

  const audits = [];
  let totalScore = 0;
  let maxScore = 0;

  // 1. Strict-Transport-Security (HSTS)
  const hstsWeight = 20;
  maxScore += hstsWeight;
  const hstsVal = normalized['strict-transport-security'];
  if (!hstsVal) {
    audits.push({
      header: 'Strict-Transport-Security',
      name: 'HSTS (HTTP Strict Transport Security)',
      status: protocol === 'https:' ? 'FAIL' : 'INFO',
      score: 0,
      maxScore: hstsWeight,
      value: null,
      summary: 'Missing HSTS Header',
      description: 'HSTS enforces encrypted HTTPS connections and prevents SSL-stripping man-in-the-middle attacks.',
      risk: 'Attackers on local Wi-Fi or networks could downgrade HTTPS traffic to HTTP and intercept sensitive user data.',
      recommendation: 'Add Strict-Transport-Security with a max-age of at least 1 year (31536000 seconds), includeSubDomains, and preload.',
      snippets: {
        nginx: 'add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;',
        apache: 'Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"',
        express: 'app.use(helmet.hsts({ maxAge: 31536000, includeSubDomains: true, preload: true }));'
      }
    });
  } else {
    const maxAgeMatch = hstsVal.match(/max-age=(\d+)/i);
    const maxAge = maxAgeMatch ? parseInt(maxAgeMatch[1], 10) : 0;
    const hasSubdomains = /includeSubDomains/i.test(hstsVal);
    const hasPreload = /preload/i.test(hstsVal);

    if (maxAge >= 31536000 && hasSubdomains) {
      totalScore += hstsWeight;
      audits.push({
        header: 'Strict-Transport-Security',
        name: 'HSTS (HTTP Strict Transport Security)',
        status: 'PASS',
        score: hstsWeight,
        maxScore: hstsWeight,
        value: hstsVal,
        summary: 'Optimal HSTS Protection',
        description: `HSTS is active with max-age=${maxAge} seconds${hasSubdomains ? ', includeSubDomains' : ''}${hasPreload ? ', preload' : ''}.`,
        risk: 'None. Browser will force HTTPS for all future visits.',
        recommendation: 'Maintain existing HSTS directive.',
        snippets: null
      });
    } else {
      const partialScore = Math.floor(hstsWeight * 0.5);
      totalScore += partialScore;
      audits.push({
        header: 'Strict-Transport-Security',
        name: 'HSTS (HTTP Strict Transport Security)',
        status: 'WARN',
        score: partialScore,
        maxScore: hstsWeight,
        value: hstsVal,
        summary: 'Weak HSTS Configuration',
        description: `HSTS is present but max-age (${maxAge}s) is under 1 year (31536000s) or missing includeSubDomains.`,
        risk: 'Subdomains or long-term return visitors may not be fully protected against protocol downgrade attacks.',
        recommendation: 'Increase max-age to 31536000 and append includeSubDomains.',
        snippets: {
          nginx: 'add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;',
          apache: 'Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"',
          express: 'app.use(helmet.hsts({ maxAge: 31536000, includeSubDomains: true }));'
        }
      });
    }
  }

  // 2. Content-Security-Policy (CSP)
  const cspWeight = 25;
  maxScore += cspWeight;
  const cspVal = normalized['content-security-policy'];
  if (!cspVal) {
    audits.push({
      header: 'Content-Security-Policy',
      name: 'CSP (Content Security Policy)',
      status: 'FAIL',
      score: 0,
      maxScore: cspWeight,
      value: null,
      summary: 'Missing CSP Header',
      description: 'CSP controls which domains and resources (scripts, images, styles) can be loaded and executed by the browser.',
      risk: 'High risk of Cross-Site Scripting (XSS), clickjacking, and data injection attacks.',
      recommendation: 'Define a strict Content-Security-Policy restricting object-src, script-src, and default-src.',
      snippets: {
        nginx: "add_header Content-Security-Policy \"default-src 'self'; script-src 'self'; object-src 'none';\" always;",
        apache: "Header always set Content-Security-Policy \"default-src 'self'; script-src 'self'; object-src 'none';\"",
        express: "app.use(helmet.contentSecurityPolicy({ directives: { defaultSrc: [\"'self'\"], scriptSrc: [\"'self'\"] } }));"
      }
    });
  } else {
    const hasUnsafeInline = /'unsafe-inline'/i.test(cspVal);
    const hasUnsafeEval = /'unsafe-eval'/i.test(cspVal);
    
    if (!hasUnsafeInline && !hasUnsafeEval) {
      totalScore += cspWeight;
      audits.push({
        header: 'Content-Security-Policy',
        name: 'CSP (Content Security Policy)',
        status: 'PASS',
        score: cspWeight,
        maxScore: cspWeight,
        value: cspVal,
        summary: 'Strong CSP Implemented',
        description: 'CSP is defined without dangerous directives like unsafe-inline or unsafe-eval.',
        risk: 'Minimal XSS and injection vulnerability footprint.',
        recommendation: 'Regularly audit CSP directives when adding new third-party scripts.',
        snippets: null
      });
    } else {
      const partialScore = Math.floor(cspWeight * 0.4);
      totalScore += partialScore;
      audits.push({
        header: 'Content-Security-Policy',
        name: 'CSP (Content Security Policy)',
        status: 'WARN',
        score: partialScore,
        maxScore: cspWeight,
        value: cspVal,
        summary: 'CSP Contains Weak Directives',
        description: `CSP is set, but includes ${hasUnsafeInline ? "'unsafe-inline'" : ''}${hasUnsafeEval ? " 'unsafe-eval'" : ''}.`,
        risk: 'Allows execution of inline scripts or dynamic strings, weakening XSS protections.',
        recommendation: 'Remove unsafe-inline and unsafe-eval by using nonces or hashes for scripts.',
        snippets: {
          nginx: "add_header Content-Security-Policy \"default-src 'self'; script-src 'self' 'nonce-rAnd0m';\" always;",
          apache: "Header always set Content-Security-Policy \"default-src 'self'; script-src 'self' 'nonce-rAnd0m';\""
        }
      });
    }
  }

  // 3. X-Frame-Options
  const xfoWeight = 15;
  maxScore += xfoWeight;
  const xfoVal = normalized['x-frame-options'];
  if (!xfoVal) {
    // Check if CSP has frame-ancestors
    const cspHasFrameAncestors = cspVal && /frame-ancestors/i.test(cspVal);
    if (cspHasFrameAncestors) {
      totalScore += xfoWeight;
      audits.push({
        header: 'X-Frame-Options',
        name: 'X-Frame-Options (Clickjacking Protection)',
        status: 'PASS',
        score: xfoWeight,
        maxScore: xfoWeight,
        value: null,
        summary: 'Covered by CSP frame-ancestors',
        description: 'X-Frame-Options header is absent, but modern clickjacking defense is satisfied by CSP frame-ancestors.',
        risk: 'Protected in modern browsers; legacy browsers may still require X-Frame-Options.',
        recommendation: 'Consider providing X-Frame-Options DENY or SAMEORIGIN as a fallback for legacy browsers.',
        snippets: {
          nginx: 'add_header X-Frame-Options "SAMEORIGIN" always;'
        }
      });
    } else {
      audits.push({
        header: 'X-Frame-Options',
        name: 'X-Frame-Options (Clickjacking Protection)',
        status: 'FAIL',
        score: 0,
        maxScore: xfoWeight,
        value: null,
        summary: 'Missing Clickjacking Defense',
        description: 'X-Frame-Options prevents the website from being embedded inside an <iframe> on external malicious sites.',
        risk: 'Vulnerable to Clickjacking attacks where attackers overlay invisible frames to hijack user clicks.',
        recommendation: 'Set X-Frame-Options to DENY or SAMEORIGIN.',
        snippets: {
          nginx: 'add_header X-Frame-Options "DENY" always;',
          apache: 'Header always set X-Frame-Options "DENY"',
          express: 'app.use(helmet.frameguard({ action: "deny" }));'
        }
      });
    }
  } else {
    const valUpper = xfoVal.toUpperCase();
    if (valUpper.includes('DENY') || valUpper.includes('SAMEORIGIN')) {
      totalScore += xfoWeight;
      audits.push({
        header: 'X-Frame-Options',
        name: 'X-Frame-Options (Clickjacking Protection)',
        status: 'PASS',
        score: xfoWeight,
        maxScore: xfoWeight,
        value: xfoVal,
        summary: 'Clickjacking Protection Configured',
        description: `X-Frame-Options set to ${xfoVal}. Embeddings are restricted.`,
        risk: 'None.',
        recommendation: 'Keep setting intact.',
        snippets: null
      });
    } else {
      audits.push({
        header: 'X-Frame-Options',
        name: 'X-Frame-Options (Clickjacking Protection)',
        status: 'WARN',
        score: 5,
        maxScore: xfoWeight,
        value: xfoVal,
        summary: 'Non-standard X-Frame-Options',
        description: `Value '${xfoVal}' may not be recognized by standard browsers.`,
        risk: 'Could allow unexpected embedding.',
        recommendation: 'Use standard values: DENY or SAMEORIGIN.',
        snippets: {
          nginx: 'add_header X-Frame-Options "SAMEORIGIN" always;'
        }
      });
    }
  }

  // 4. X-Content-Type-Options
  const xctoWeight = 15;
  maxScore += xctoWeight;
  const xctoVal = normalized['x-content-type-options'];
  if (!xctoVal) {
    audits.push({
      header: 'X-Content-Type-Options',
      name: 'X-Content-Type-Options (MIME-Sniffing Guard)',
      status: 'FAIL',
      score: 0,
      maxScore: xctoWeight,
      value: null,
      summary: 'Missing MIME-Sniffing Guard',
      description: 'Prevents browsers from MIME-sniffing a response away from the declared content-type.',
      risk: 'Attackers can upload malicious script files masquerading as images/text and execute them on the client.',
      recommendation: 'Set X-Content-Type-Options to nosniff.',
      snippets: {
        nginx: 'add_header X-Content-Type-Options "nosniff" always;',
        apache: 'Header always set X-Content-Type-Options "nosniff"',
        express: 'app.use(helmet.noSniff());'
      }
    });
  } else if (xctoVal.toLowerCase().includes('nosniff')) {
    totalScore += xctoWeight;
    audits.push({
      header: 'X-Content-Type-Options',
      name: 'X-Content-Type-Options (MIME-Sniffing Guard)',
      status: 'PASS',
      score: xctoWeight,
      maxScore: xctoWeight,
      value: xctoVal,
      summary: 'MIME-Sniffing Blocked',
      description: 'X-Content-Type-Options is set to nosniff. Browser will respect declared Content-Type header.',
      risk: 'None.',
      recommendation: 'Keep setting intact.',
      snippets: null
    });
  } else {
    audits.push({
      header: 'X-Content-Type-Options',
      name: 'X-Content-Type-Options (MIME-Sniffing Guard)',
      status: 'WARN',
      score: 5,
      maxScore: xctoWeight,
      value: xctoVal,
      summary: 'Invalid X-Content-Type-Options Value',
      description: `Value '${xctoVal}' should be 'nosniff'.`,
      risk: 'Browsers may ignore the header.',
      recommendation: 'Set value explicitly to nosniff.',
      snippets: {
        nginx: 'add_header X-Content-Type-Options "nosniff" always;'
      }
    });
  }

  // 5. Referrer-Policy
  const rpWeight = 15;
  maxScore += rpWeight;
  const rpVal = normalized['referrer-policy'];
  if (!rpVal) {
    audits.push({
      header: 'Referrer-Policy',
      name: 'Referrer-Policy (Privacy & Information Leakage)',
      status: 'WARN',
      score: 5,
      maxScore: rpWeight,
      value: null,
      summary: 'Missing Referrer-Policy',
      description: 'Controls how much HTTP referrer information is sent along with outbound requests.',
      risk: 'Sensitive URL parameters (e.g. reset tokens, session IDs) might leak to third-party domains.',
      recommendation: 'Set Referrer-Policy to strict-origin-when-cross-origin or no-referrer.',
      snippets: {
        nginx: 'add_header Referrer-Policy "strict-origin-when-cross-origin" always;',
        apache: 'Header always set Referrer-Policy "strict-origin-when-cross-origin"',
        express: 'app.use(helmet.referrerPolicy({ policy: "strict-origin-when-cross-origin" }));'
      }
    });
  } else {
    totalScore += rpWeight;
    audits.push({
      header: 'Referrer-Policy',
      name: 'Referrer-Policy (Privacy & Information Leakage)',
      status: 'PASS',
      score: rpWeight,
      maxScore: rpWeight,
      value: rpVal,
      summary: 'Referrer Policy Active',
      description: `Referrer Policy is set to '${rpVal}'.`,
      risk: 'Protected against inadvertent URL leakage.',
      recommendation: 'Maintain configured policy.',
      snippets: null
    });
  }

  // 6. Permissions-Policy
  const ppWeight = 10;
  maxScore += ppWeight;
  const ppVal = normalized['permissions-policy'] || normalized['feature-policy'];
  if (!ppVal) {
    audits.push({
      header: 'Permissions-Policy',
      name: 'Permissions-Policy (Browser Feature Access)',
      status: 'INFO',
      score: 5,
      maxScore: ppWeight,
      value: null,
      summary: 'Permissions-Policy Not Explicitly Set',
      description: 'Allows restriction of hardware features like camera, microphone, geolocation, and payment API.',
      risk: 'Embedded scripts could trigger browser permissions prompts.',
      recommendation: 'Configure Permissions-Policy to explicitly disable unused hardware APIs.',
      snippets: {
        nginx: 'add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;',
        apache: 'Header always set Permissions-Policy "geolocation=(), microphone=(), camera=()"'
      }
    });
  } else {
    totalScore += ppWeight;
    audits.push({
      header: 'Permissions-Policy',
      name: 'Permissions-Policy (Browser Feature Access)',
      status: 'PASS',
      score: ppWeight,
      maxScore: ppWeight,
      value: ppVal,
      summary: 'Permissions-Policy Configured',
      description: `Feature permissions restricted via '${ppVal}'.`,
      risk: 'None.',
      recommendation: 'Maintain feature policy configuration.',
      snippets: null
    });
  }

  const percentage = Math.round((totalScore / maxScore) * 100);
  let grade = 'F';
  let color = 'rose';

  if (percentage >= 90) {
    grade = 'A+';
    color = 'emerald';
  } else if (percentage >= 80) {
    grade = 'A';
    color = 'emerald';
  } else if (percentage >= 70) {
    grade = 'B';
    color = 'cyan';
  } else if (percentage >= 60) {
    grade = 'C';
    color = 'amber';
  } else if (percentage >= 40) {
    grade = 'D';
    color = 'orange';
  } else {
    grade = 'F';
    color = 'rose';
  }

  const summaryCounts = {
    pass: audits.filter(a => a.status === 'PASS').length,
    warn: audits.filter(a => a.status === 'WARN').length,
    fail: audits.filter(a => a.status === 'FAIL').length,
    info: audits.filter(a => a.status === 'INFO').length
  };

  return {
    score: percentage,
    grade,
    gradeColor: color,
    summaryCounts,
    audits
  };
}

module.exports = {
  analyzeHeaders
};
