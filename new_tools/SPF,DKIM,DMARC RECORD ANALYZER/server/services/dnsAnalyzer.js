import dns from 'node:dns/promises';

export const DEFAULT_DKIM_SELECTORS = [
  'google',
  'selector1',
  'selector2',
  's1',
  's2',
  'default',
  'k1',
  'mail',
];

/**
 * Execute a DNS TXT lookup with explicit timeout (5s default)
 */
async function resolveTxtWithTimeout(domain, timeoutMs = 5000) {
  let timeoutId;
  const timeoutPromise = new Promise((_, reject) => {
    timeoutId = setTimeout(() => {
      const err = new Error(`DNS lookup timed out after ${timeoutMs}ms for ${domain}`);
      err.code = 'ETIMEDOUT';
      reject(err);
    }, timeoutMs);
  });

  try {
    const resolver = new dns.Resolver();
    resolver.setServers(['8.8.8.8', '1.1.1.1']); // Google & Cloudflare public DNS
    const txtPromise = resolver.resolveTxt(domain);
    const records = await Promise.race([txtPromise, timeoutPromise]);
    clearTimeout(timeoutId);

    // resolver.resolveTxt returns array of arrays of strings: [ ['v=spf1 ...'] ]
    return records.map((chunks) => chunks.join(''));
  } catch (error) {
    clearTimeout(timeoutId);
    if (['ENOTFOUND', 'ENODATA', 'NXDOMAIN'].includes(error.code)) {
      return [];
    }
    if (error.code === 'ETIMEDOUT') {
      throw error;
    }
    return [];
  }
}

/**
 * Parses raw SPF record text into mechanisms, qualifiers, and metadata
 */
export function parseSpfMechanisms(recordText) {
  const raw = String(recordText || '').trim();
  const tokens = raw.split(/\s+/).filter(Boolean);
  
  const mechanisms = [];
  let terminalQualifier = 'none';
  const issues = [];

  if (!raw.toLowerCase().startsWith('v=spf1')) {
    issues.push('SPF record does not begin with standard "v=spf1" prefix.');
  }

  for (const token of tokens) {
    if (token.toLowerCase() === 'v=spf1') continue;

    // Check terminal 'all' qualifier
    const allMatch = token.match(/^([-~?+]?)all$/i);
    if (allMatch) {
      const prefix = allMatch[1] || '+';
      terminalQualifier = `${prefix}all`.toLowerCase();
      
      if (terminalQualifier === '+all') {
        issues.push('CRITICAL: "+all" qualifier permits ANY host on the internet to pass SPF checks for this domain.');
      } else if (terminalQualifier === '?all') {
        issues.push('WARNING: "?all" (Neutral) qualifier specifies no policy enforcement for unauthorized senders.');
      }
      continue;
    }

    // Match mechanisms
    const match = token.match(/^([-~?+]?)(include:|redirect=|ip4:|ip6:|a|mx|ptr|exists:)(.*)$/i);
    if (match) {
      mechanisms.push({
        raw: token,
        qualifier: match[1] || '+',
        type: match[2].replace(/[:=]/, '').toLowerCase(),
        target: match[3] || '',
      });
    } else if (token.startsWith('ip4:') || token.startsWith('ip6:')) {
      mechanisms.push({
        raw: token,
        qualifier: '+',
        type: token.substring(0, 3).toLowerCase(),
        target: token.substring(4),
      });
    }
  }

  if (terminalQualifier === 'none') {
    issues.push('WARNING: No terminal "all" mechanism (e.g. -all or ~all) was found in the SPF record.');
  }

  return { raw, tokens, mechanisms, terminalQualifier, issues };
}

/**
 * Recursively resolves SPF includes/redirects and counts total DNS lookups (RFC 7208 §4.6.4 cap = 10)
 */
export async function analyzeSpf(domain) {
  const issues = [];
  const lookupTree = [];
  let totalLookups = 0;
  const visitedDomains = new Set();

  async function traceSpf(targetDomain, currentDepth = 0) {
    if (visitedDomains.has(targetDomain.toLowerCase())) {
      issues.push(`Circular SPF inclusion detected for domain "${targetDomain}".`);
      return { domain: targetDomain, record: null, childLookups: 0, circular: true };
    }
    visitedDomains.add(targetDomain.toLowerCase());

    const txtRecords = await resolveTxtWithTimeout(targetDomain);
    const spfRecords = txtRecords.filter((r) => r.toLowerCase().startsWith('v=spf1'));

    if (spfRecords.length === 0) {
      return { domain: targetDomain, record: null, childLookups: 0, error: 'No SPF record found' };
    }

    if (spfRecords.length > 1 && currentDepth === 0) {
      issues.push(`RFC 7208 Violation: Domain "${targetDomain}" publishes multiple SPF records (${spfRecords.length}). Receiving MTAs will evaluate this as PermError.`);
    }

    const record = spfRecords[0];
    const parsed = parseSpfMechanisms(record);

    if (currentDepth === 0) {
      issues.push(...parsed.issues);
    }

    const node = {
      domain: targetDomain,
      record,
      terminalQualifier: parsed.terminalQualifier,
      mechanismsCounted: [],
      children: [],
    };

    for (const mech of parsed.mechanisms) {
      const type = mech.type.toLowerCase();

      // Mechanisms that cause a DNS lookup per RFC 7208 §4.6.4:
      // include, a, mx, ptr, exists, redirect
      if (['include', 'a', 'mx', 'ptr', 'exists', 'redirect'].includes(type)) {
        totalLookups++;
        node.mechanismsCounted.push({ type, raw: mech.raw, lookupIndex: totalLookups });

        if ((type === 'include' || type === 'redirect') && mech.target) {
          if (currentDepth < 5) {
            const childNode = await traceSpf(mech.target, currentDepth + 1);
            node.children.push(childNode);
          }
        }
      }
    }

    return node;
  }

  try {
    const tree = await traceSpf(domain);
    lookupTree.push(tree);

    const recordFound = Boolean(tree && tree.record);
    const maxLookupsExceeded = totalLookups > 10;

    if (maxLookupsExceeded) {
      issues.push(
        `RFC 7208 Cap Violation: SPF record generated ${totalLookups} DNS lookups (RFC limit is 10). Receiving servers will return PermError and reject/fail SPF.`
      );
    }

    return {
      found: recordFound,
      valid: recordFound && !maxLookupsExceeded && !issues.some((i) => i.startsWith('RFC') || i.startsWith('CRITICAL')),
      record: tree.record || null,
      lookupCount: totalLookups,
      maxLookupsExceeded,
      terminalQualifier: tree.terminalQualifier || 'none',
      issues,
      lookupTree,
    };
  } catch (error) {
    if (error.code === 'ETIMEDOUT') {
      return {
        found: false,
        valid: false,
        record: null,
        lookupCount: 0,
        maxLookupsExceeded: false,
        terminalQualifier: 'none',
        issues: [`DNS lookup timed out while resolving SPF record for ${domain}.`],
        lookupTree: [],
      };
    }
    throw error;
  }
}

/**
 * Parses DKIM TXT record tag-value pairs
 */
export function parseDkimRecord(recordText = '') {
  const raw = String(recordText).trim();
  if (!raw) {
    return { found: false, valid: false, record: null, issues: ['No DKIM TXT record published for this selector.'] };
  }

  const tags = {};
  const issues = [];

  // Parse tag=value pairs separated by semicolon
  const parts = raw.split(';').map((p) => p.trim()).filter(Boolean);
  for (const part of parts) {
    const eqIdx = part.indexOf('=');
    if (eqIdx !== -1) {
      const key = part.slice(0, eqIdx).trim().toLowerCase();
      const val = part.slice(eqIdx + 1).trim();
      tags[key] = val;
    }
  }

  const keyType = (tags.k || 'rsa').toLowerCase();
  const publicKey = tags.p || '';
  const revoked = publicKey === '';

  if (revoked) {
    issues.push('DKIM public key (p=) is empty. This key has been REVOKED by the domain owner (RFC 6376).');
  } else if (!/^[A-Za-z0-9+/=]+$/.test(publicKey.replace(/\s+/g, ''))) {
    issues.push('DKIM public key contains invalid non-base64 characters.');
  }

  return {
    found: true,
    valid: issues.length === 0 && !revoked,
    record: raw,
    keyType,
    publicKeyLength: publicKey ? publicKey.length * 6 : 0, // rough bit estimation
    revoked,
    tags,
    issues,
  };
}

/**
 * Analyzes DKIM selectors for a domain
 */
export async function analyzeDkim(domain, userSelectors = []) {
  const selectorsToCheck = [
    ...new Set([
      ...(Array.isArray(userSelectors) ? userSelectors : []),
      ...DEFAULT_DKIM_SELECTORS,
    ]),
  ].filter(Boolean);

  const results = [];

  for (const selector of selectorsToCheck) {
    const fqdn = `${selector}._domainkey.${domain}`;
    try {
      const txtRecords = await resolveTxtWithTimeout(fqdn);
      const dkimTxt = txtRecords.find((r) => r.includes('p=') || r.includes('v=DKIM1') || r.includes('k='));

      if (dkimTxt) {
        const parsed = parseDkimRecord(dkimTxt);
        results.push({
          selector,
          fqdn,
          found: true,
          valid: parsed.valid,
          record: dkimTxt,
          keyType: parsed.keyType,
          revoked: parsed.revoked,
          issues: parsed.issues,
        });
      } else {
        results.push({
          selector,
          fqdn,
          found: false,
          valid: false,
          record: null,
          issues: ['No DKIM TXT record found at this selector.'],
        });
      }
    } catch (error) {
      results.push({
        selector,
        fqdn,
        found: false,
        valid: false,
        record: null,
        issues: [error.message || 'Lookup failed.'],
      });
    }
  }

  const foundCount = results.filter((r) => r.found).length;

  return {
    selectorsChecked: selectorsToCheck,
    foundCount,
    results,
  };
}

/**
 * Parses DMARC TXT record
 */
export function parseDmarcRecord(recordText = '') {
  const raw = String(recordText).trim();
  const issues = [];

  if (!raw) {
    return {
      found: false,
      valid: false,
      record: null,
      policy: 'none',
      subdomainPolicy: 'none',
      pct: 100,
      rua: [],
      ruf: [],
      alignment: { spf: 'relaxed', dkim: 'relaxed' },
      issues: ['No DMARC record found at _dmarc.<domain>.'],
    };
  }

  if (!raw.toLowerCase().startsWith('v=dmarc1')) {
    issues.push('DMARC record does not start with compulsory "v=DMARC1" prefix.');
  }

  const tags = {};
  const parts = raw.split(';').map((p) => p.trim()).filter(Boolean);
  for (const part of parts) {
    const eqIdx = part.indexOf('=');
    if (eqIdx !== -1) {
      const key = part.slice(0, eqIdx).trim().toLowerCase();
      const val = part.slice(eqIdx + 1).trim();
      tags[key] = val;
    }
  }

  const policy = (tags.p || 'none').toLowerCase();
  const subdomainPolicy = (tags.sp || policy).toLowerCase();
  const pct = Number(tags.pct || '100');
  const adkim = (tags.adkim || 'r').toLowerCase() === 's' ? 'strict' : 'relaxed';
  const aspf = (tags.aspf || 'r').toLowerCase() === 's' ? 'strict' : 'relaxed';

  const parseUris = (str) =>
    (str || '')
      .split(',')
      .map((u) => u.trim())
      .filter(Boolean);

  const rua = parseUris(tags.rua);
  const ruf = parseUris(tags.ruf);

  if (policy === 'none') {
    issues.push('POLICY WARNING: DMARC policy is set to "p=none" (monitoring mode). Emails failing authentication will NOT be rejected or quarantined.');
  } else if (policy === 'quarantine') {
    issues.push('POLICY INFO: DMARC policy is set to "p=quarantine". Failing emails will be sent to Spam/Junk folders.');
  }

  if (pct < 100) {
    issues.push(`POLICY NOTICE: DMARC policy applies to only ${pct}% of messages (pct=${pct}).`);
  }

  if (rua.length === 0) {
    issues.push('REPORTING WARNING: No aggregate report URI (rua=) configured. You will not receive XML deliverability and spoofing telemetry.');
  }

  return {
    found: true,
    valid: issues.filter((i) => i.startsWith('RFC') || i.startsWith('CRITICAL')).length === 0,
    record: raw,
    policy,
    subdomainPolicy,
    pct,
    rua,
    ruf,
    alignment: {
      spf: aspf,
      dkim: adkim,
    },
    issues,
  };
}

/**
 * Analyzes DMARC record for a domain
 */
export async function analyzeDmarc(domain) {
  const fqdn = `_dmarc.${domain}`;
  try {
    const txtRecords = await resolveTxtWithTimeout(fqdn);
    const dmarcRecords = txtRecords.filter((r) => r.toLowerCase().startsWith('v=dmarc1'));

    if (dmarcRecords.length === 0) {
      return parseDmarcRecord('');
    }

    const issues = [];
    if (dmarcRecords.length > 1) {
      issues.push(`RFC 7489 Violation: Multiple DMARC records (${dmarcRecords.length}) published at ${fqdn}. Receivers will ignore all DMARC records.`);
    }

    const parsed = parseDmarcRecord(dmarcRecords[0]);
    parsed.issues.unshift(...issues);

    return parsed;
  } catch (error) {
    if (error.code === 'ETIMEDOUT') {
      return {
        found: false,
        valid: false,
        record: null,
        policy: 'none',
        issues: [`DNS lookup timed out while resolving DMARC record for ${fqdn}.`],
      };
    }
    throw error;
  }
}

/**
 * Calculates overall domain authentication score
 */
export function calculateOverallScore(spf, dkim, dmarc) {
  const hasSpf = spf && spf.found && !spf.maxLookupsExceeded && spf.terminalQualifier !== '+all';
  const hasDmarcEnforcement = dmarc && dmarc.found && (dmarc.policy === 'quarantine' || dmarc.policy === 'reject');
  const hasDmarc = dmarc && dmarc.found;
  const hasDkimFound = dkim && dkim.foundCount > 0;

  if (hasSpf && hasDmarcEnforcement && hasDkimFound) {
    return 'Good';
  }

  if (hasSpf && hasDmarc) {
    return 'Needs Improvement';
  }

  return 'Poor';
}
