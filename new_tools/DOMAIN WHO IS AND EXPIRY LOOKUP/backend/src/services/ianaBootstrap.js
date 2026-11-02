const axios = require('axios');
const net = require('net');
const TldServerMap = require('../models/TldServerMap');

// Fallback hardcoded server map for instant lookups on major TLDs
const FALLBACK_TLD_MAP = {
  com: { whois: 'whois.verisign-grs.com', rdap: ['https://rdap.verisign.com/com/v1/'] },
  net: { whois: 'whois.verisign-grs.com', rdap: ['https://rdap.verisign.com/net/v1/'] },
  org: { whois: 'whois.publicinterestregistry.org', rdap: ['https://rdap.publicinterestregistry.org/rdap/'] },
  in: { whois: 'whois.registry.in', rdap: ['https://rdap.registry.in/'] },
  io: { whois: 'whois.nic.io', rdap: ['https://rdap.nic.io/'] },
  co: { whois: 'whois.nic.co', rdap: ['https://rdap.nic.co/'] },
  uk: { whois: 'whois.nic.uk', rdap: [] },
  dev: { whois: 'whois.nic.google', rdap: ['https://rdap.nic.google/'] },
  app: { whois: 'whois.nic.google', rdap: ['https://rdap.nic.google/'] },
  ai: { whois: 'whois.nic.ai', rdap: [] },
  me: { whois: 'whois.nic.me', rdap: [] },
  info: { whois: 'whois.afilias.net', rdap: ['https://rdap.afilias.net/rdap/'] },
  biz: { whois: 'whois.nic.biz', rdap: ['https://rdap.nic.biz/'] },
};

let rdapBootstrapCache = null;
let lastBootstrapFetch = 0;
const BOOTSTRAP_CACHE_TTL_MS = 24 * 60 * 60 * 1000; // 24 hours

/**
 * Fetches IANA RDAP Bootstrap DNS json
 */
async function fetchIanaRdapBootstrap() {
  if (rdapBootstrapCache && Date.now() - lastBootstrapFetch < BOOTSTRAP_CACHE_TTL_MS) {
    return rdapBootstrapCache;
  }

  try {
    const response = await axios.get('https://data.iana.org/rdap/dns.json', { timeout: 8000 });
    if (response.data && response.data.services) {
      rdapBootstrapCache = response.data.services;
      lastBootstrapFetch = Date.now();
      console.log(`[IANA Bootstrap] Updated RDAP bootstrap registry with ${rdapBootstrapCache.length} service blocks.`);
      return rdapBootstrapCache;
    }
  } catch (err) {
    console.warn(`[IANA Bootstrap] Failed to fetch IANA RDAP bootstrap registry: ${err.message}. Using fallback map.`);
  }

  return rdapBootstrapCache;
}

/**
 * Queries whois.iana.org over TCP port 43 to discover the authoritative registry WHOIS server for a TLD.
 */
function queryIanaWhois(tld, timeoutMs = 8000) {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    let responseData = '';

    socket.setTimeout(timeoutMs);

    socket.connect(43, 'whois.iana.org', () => {
      socket.write(`${tld}\r\n`);
    });

    socket.on('data', (chunk) => {
      responseData += chunk.toString();
    });

    socket.on('timeout', () => {
      socket.destroy();
      resolve(null);
    });

    socket.on('error', () => {
      socket.destroy();
      resolve(null);
    });

    socket.on('close', () => {
      if (!responseData) return resolve(null);

      // Parse refer / whois line from IANA response
      const lines = responseData.split('\n');
      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.toLowerCase().startsWith('whois:') || trimmed.toLowerCase().startsWith('refer:')) {
          const server = trimmed.split(':')[1]?.trim();
          if (server) return resolve(server);
        }
      }

      resolve(null);
    });
  });
}

/**
 * Resolves RDAP base URLs and WHOIS server for a given TLD.
 * @param {string} tld
 * @returns {Promise<{ rdapUrls: string[], whoisServer: string|null }>}
 */
async function resolveTldAuthority(tld) {
  const normalizedTld = tld.toLowerCase().replace(/^\./, '');

  // 1. Check MongoDB cache first if DB is available
  try {
    const cachedMap = await TldServerMap.findOne({ tld: normalizedTld });
    if (cachedMap && (cachedMap.rdapUrls?.length > 0 || cachedMap.whoisServer)) {
      return {
        rdapUrls: cachedMap.rdapUrls || [],
        whoisServer: cachedMap.whoisServer || null,
      };
    }
  } catch (err) {
    // Silent fail over DB errors
  }

  // 2. Check IANA RDAP Bootstrap Registry
  let rdapUrls = [];
  const services = await fetchIanaRdapBootstrap();
  if (services) {
    for (const [tldList, urls] of services) {
      if (tldList.includes(normalizedTld)) {
        rdapUrls = urls;
        break;
      }
    }
  }

  // 3. Fallback to hardcoded map if RDAP URLs not found in IANA json
  let whoisServer = FALLBACK_TLD_MAP[normalizedTld]?.whois || null;
  if (!rdapUrls.length && FALLBACK_TLD_MAP[normalizedTld]?.rdap) {
    rdapUrls = FALLBACK_TLD_MAP[normalizedTld].rdap;
  }

  // 4. If no whois server yet, query whois.iana.org over port 43
  if (!whoisServer) {
    whoisServer = await queryIanaWhois(normalizedTld);
  }

  // 5. Store resolved mapping in MongoDB cache if available
  try {
    await TldServerMap.findOneAndUpdate(
      { tld: normalizedTld },
      { tld: normalizedTld, rdapUrls, whoisServer, lastFetchedAt: new Date() },
      { upsert: true, new: true }
    );
  } catch (err) {
    // DB save fail non-fatal
  }

  return {
    rdapUrls,
    whoisServer: whoisServer || `whois.nic.${normalizedTld}`,
  };
}

module.exports = {
  fetchIanaRdapBootstrap,
  resolveTldAuthority,
  queryIanaWhois,
  FALLBACK_TLD_MAP,
};
