const crypto = require('crypto');
const Lookup = require('../models/Lookup');
const WhoisCache = require('../models/WhoisCache');
const { normalizeDomain } = require('./domainNormalizer');
const { resolveTldAuthority } = require('./ianaBootstrap');
const { queryRdap } = require('./rdapClient');
const { queryWhois } = require('./whoisClient');

const CACHE_TTL_SECONDS = parseInt(process.env.CACHE_TTL_SECONDS || '3600', 10);

/**
 * Creates SHA-256 hash of requester IP for privacy-preserving logging
 * @param {string} ip
 * @returns {string}
 */
function hashIp(ip) {
  if (!ip) return 'anonymous_hash';
  return crypto.createHash('sha256').update(ip).digest('hex');
}

/**
 * Performs full WHOIS / RDAP lookup flow for a domain.
 * @param {string} rawInput
 * @param {string} clientIp
 * @param {boolean} forceRefresh
 * @param {string|null} sessionId
 * @returns {Promise<object>}
 */
async function performLookup(rawInput, clientIp = '127.0.0.1', forceRefresh = false, sessionId = null) {
  // 1. Normalize and validate domain
  const normalized = normalizeDomain(rawInput);
  if (!normalized.isValid) {
    return {
      success: false,
      error: normalized.error,
    };
  }

  const { domain, asciiDomain, tld } = normalized;
  const ipHash = hashIp(clientIp);

  // 2. Check Cache if not forcing refresh
  if (!forceRefresh) {
    try {
      const cached = await WhoisCache.findOne({ domain });
      if (cached && cached.expiresAt > new Date()) {
        const cachedData = {
          ...cached.data,
          fromCache: true,
          cachedAt: cached.createdAt,
        };

        // Log lookup event asynchronously
        saveLookupLog(domain, tld, 'cache', cachedData, ipHash, sessionId);

        return {
          success: true,
          data: cachedData,
        };
      }
    } catch (err) {
      console.warn(`[Lookup Service] Cache read error: ${err.message}`);
    }
  }

  // 3. Resolve Authority (RDAP URLs & WHOIS Server)
  const authority = await resolveTldAuthority(tld);

  let result = null;
  let lookupSource = 'rdap';

  // 4. Try RDAP Client first if RDAP URLs exist
  if (authority.rdapUrls && authority.rdapUrls.length > 0) {
    try {
      result = await queryRdap(asciiDomain, authority.rdapUrls);
    } catch (err) {
      console.warn(`[Lookup Service] RDAP lookup failed for ${asciiDomain}: ${err.message}. Falling back to WHOIS port 43.`);
    }
  }

  // 5. Fall back to WHOIS Client over TCP port 43 if RDAP yields no result
  if (!result) {
    lookupSource = 'whois';
    try {
      result = await queryWhois(asciiDomain, authority.whoisServer);
    } catch (err) {
      console.error(`[Lookup Service] WHOIS lookup failed for ${asciiDomain}: ${err.message}`);
      return {
        success: false,
        error: `Unable to retrieve WHOIS/RDAP records for domain "${domain}". The TLD registry server (${authority.whoisServer || 'TLD authority'}) timed out or rejected the connection.`,
      };
    }
  }

  // Ensure result retains requested user domain name for display
  result.domain = domain;
  result.tld = tld;
  result.fromCache = false;

  // 6. Save to Cache asynchronously if result is valid
  if (result && result.status !== 'error') {
    const expiresAt = new Date(Date.now() + CACHE_TTL_SECONDS * 1000);
    WhoisCache.findOneAndUpdate(
      { domain },
      { domain, tld, data: result, expiresAt },
      { upsert: true, new: true }
    ).catch((err) => console.warn(`[Lookup Service] Cache write error: ${err.message}`));
  }

  // 7. Save Lookup Log asynchronously
  saveLookupLog(domain, tld, lookupSource, result, ipHash, sessionId);

  return {
    success: true,
    data: result,
  };
}

/**
 * Asynchronous helper to record audit lookup log to DB
 */
function saveLookupLog(domain, tld, source, data, ipHash, sessionId = null) {
  Lookup.create({
    domain,
    tld,
    source: source,
    status: data.status || 'active',
    daysRemaining: data.daysRemaining,
    registrar: data.registrar,
    createdDate: data.createdDate ? new Date(data.createdDate) : null,
    expiresDate: data.expiresDate ? new Date(data.expiresDate) : null,
    updatedDate: data.updatedDate ? new Date(data.updatedDate) : null,
    nameServers: data.nameServers || [],
    statusFlags: data.statusFlags || [],
    parsedStatusDetails: data.parsedStatusDetails || [],
    dnssec: data.dnssec || 'unknown',
    privacyProtected: !!data.privacyProtected,
    registrantOrg: data.registrantOrg,
    requesterIpHash: ipHash,
    sessionId: sessionId || null,
    checkedAt: new Date(),
  }).catch((err) => console.warn(`[Lookup Service] Audit log creation failed: ${err.message}`));
}

/**
 * Fetches recent lookups for frontend feed (global or personal "my" history)
 */
async function getHistory({ type = 'global', sessionId = null, clientIp = null, limit = 10 }) {
  try {
    let query = {};

    if (type === 'my') {
      const ipHash = clientIp ? hashIp(clientIp) : null;
      if (sessionId) {
        query = { sessionId };
      } else if (ipHash) {
        query = { requesterIpHash: ipHash };
      } else {
        return [];
      }
    }

    const records = await Lookup.find(query)
      .sort({ checkedAt: -1 })
      .limit(limit)
      .select('domain tld status daysRemaining checkedAt source privacyProtected sessionId')
      .lean();

    return records.map((r) => ({
      domain: r.domain,
      tld: r.tld,
      status: r.status,
      daysRemaining: r.daysRemaining,
      checkedAt: r.checkedAt,
      source: r.source,
      privacyProtected: r.privacyProtected,
      sessionId: r.sessionId,
    }));
  } catch (err) {
    return [];
  }
}

async function getRecentLookups(limit = 10) {
  return getHistory({ type: 'global', limit });
}

module.exports = {
  performLookup,
  getHistory,
  getRecentLookups,
  hashIp,
};
