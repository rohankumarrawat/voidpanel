const net = require('net');
const { parseStatusFlags } = require('./statusParser');

/**
 * Executes a raw WHOIS query over TCP port 43.
 * @param {string} domain - Domain name to query
 * @param {string} server - WHOIS server host
 * @param {number} timeoutMs - Timeout in ms
 * @returns {Promise<string>} Raw WHOIS text output
 */
function sendTcpWhoisQuery(domain, server, timeoutMs = 8000) {
  return new Promise((resolve, reject) => {
    if (!server) {
      return reject(new Error('No WHOIS server specified'));
    }

    const socket = new net.Socket();
    let data = '';

    socket.setTimeout(timeoutMs);

    // Format query string based on server nuances (Verisign requires 'domain ')
    let query = `${domain}\r\n`;
    if (server.includes('verisign-grs.com')) {
      query = `domain ${domain}\r\n`;
    }

    socket.connect(43, server, () => {
      socket.write(query);
    });

    socket.on('data', (chunk) => {
      data += chunk.toString('utf8');
    });

    socket.on('timeout', () => {
      socket.destroy();
      reject(new Error(`WHOIS query timed out connection to ${server}:43`));
    });

    socket.on('error', (err) => {
      socket.destroy();
      reject(new Error(`WHOIS socket error on ${server}:43 - ${err.message}`));
    });

    socket.on('close', () => {
      resolve(data);
    });
  });
}

/**
 * Extracts referral registrar WHOIS server from WHOIS text.
 * @param {string} whoisText
 * @returns {string|null}
 */
function extractReferralWhoisServer(whoisText) {
  if (!whoisText) return null;
  const match = whoisText.match(/(?:Registrar WHOIS Server|Whois Server|Referral Server):\s*([a-zA-Z0-9.-]+)/i);
  if (match && match[1]) {
    const foundServer = match[1].trim().toLowerCase().replace(/^https?:\/\//, '');
    // Avoid referring back to IANA or same server
    if (foundServer && !foundServer.includes('iana.org') && foundServer.length > 3) {
      return foundServer;
    }
  }
  return null;
}

/**
 * Determines if WHOIS text signifies an available/unregistered domain.
 * @param {string} text
 * @returns {boolean}
 */
function isDomainAvailableText(text) {
  if (!text) return true;
  const lower = text.toLowerCase();
  const availablePhrases = [
    'no match for',
    'not found',
    'no data found',
    'domain not found',
    'no entries found',
    'status: available',
    'is free',
    'nothing found',
    'object does not exist',
    'no match',
  ];
  return availablePhrases.some((phrase) => lower.includes(phrase));
}

/**
 * Parses raw WHOIS text response into standardized object.
 * @param {string} whoisText
 * @param {string} domain
 * @returns {object}
 */
function parseWhoisText(whoisText, domain) {
  if (!whoisText || isDomainAvailableText(whoisText)) {
    return {
      domain,
      status: 'available',
      isAvailable: true,
      source: 'whois',
      rawResponse: whoisText || 'No WHOIS response received.',
    };
  }

  const lines = whoisText.split(/\r?\n/);
  
  let registrarName = null;
  let registrarIanaId = null;
  let registrarUrl = null;
  let registrarEmail = null;
  let createdDate = null;
  let expiresDate = null;
  let updatedDate = null;
  let registrantOrg = null;
  let privacyProtected = false;
  let dnssec = 'unsigned';
  
  const nameServers = new Set();
  const statusFlags = new Set();

  for (let line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('%') || trimmed.startsWith('#') || trimmed.startsWith(';')) {
      continue;
    }

    const colonIndex = trimmed.indexOf(':');
    if (colonIndex === -1) continue;

    const key = trimmed.substring(0, colonIndex).trim().toLowerCase();
    const value = trimmed.substring(colonIndex + 1).trim();

    if (!value) continue;

    // Registrar fields
    if (key.includes('registrar') && !key.includes('whois') && !key.includes('url') && !key.includes('iana') && !registrarName) {
      registrarName = value;
    } else if (key.includes('registrar iana id') || key.includes('iana id')) {
      registrarIanaId = value;
    } else if (key.includes('registrar url')) {
      registrarUrl = value;
    } else if (key.includes('registrar abuse contact email')) {
      registrarEmail = value;
    }

    // Date fields
    if (key.includes('creation date') || key.includes('created date') || key.includes('created:') || key.includes('registered')) {
      if (!createdDate) createdDate = parseFlexibleDate(value);
    } else if (key.includes('expiry date') || key.includes('expiration date') || key.includes('expires') || key.includes('registry expiry date')) {
      if (!expiresDate) expiresDate = parseFlexibleDate(value);
    } else if (key.includes('updated date') || key.includes('last updated')) {
      if (!updatedDate) updatedDate = parseFlexibleDate(value);
    }

    // Name Servers
    if (key.includes('name server') || key.includes('nserver') || key.includes('nameserver')) {
      const nsHost = value.split(' ')[0].toLowerCase().replace(/\.$/, '');
      if (nsHost && nsHost.includes('.')) {
        nameServers.add(nsHost);
      }
    }

    // Domain Status
    if (key.includes('domain status') || key.includes('status')) {
      const statusValue = value.split(' ')[0].trim();
      if (statusValue) statusFlags.add(statusValue);
    }

    // Registrant Org / GDPR privacy check
    if (key.includes('registrant organization') || key.includes('registrant org') || key.includes('registrant name')) {
      if (value.toLowerCase().includes('redacted') || value.toLowerCase().includes('privacy') || value.toLowerCase().includes('proxy') || value.toLowerCase().includes('gdpr')) {
        privacyProtected = true;
      } else if (!registrantOrg) {
        registrantOrg = value;
      }
    }

    // Privacy indicators anywhere in line
    if (trimmed.toLowerCase().includes('redacted for privacy') || trimmed.toLowerCase().includes('data protected') || trimmed.toLowerCase().includes('privacy service')) {
      privacyProtected = true;
    }

    // DNSSEC
    if (key.includes('dnssec')) {
      const lowerVal = value.toLowerCase();
      if (lowerVal.includes('signed') || lowerVal.includes('yes') || lowerVal.includes('active')) {
        dnssec = 'signed';
      } else if (lowerVal.includes('unsigned') || lowerVal.includes('no')) {
        dnssec = 'unsigned';
      }
    }
  }

  // Days remaining & Status calculation
  let daysRemaining = null;
  let status = 'active';

  if (expiresDate) {
    const diffMs = expiresDate.getTime() - Date.now();
    daysRemaining = Math.ceil(diffMs / (1000 * 60 * 60 * 24));

    if (daysRemaining <= 0) {
      status = 'expired';
    } else if (daysRemaining <= 30) {
      status = 'expiring';
    }
  }

  if (privacyProtected && status === 'active') {
    status = 'privacy_protected';
  }

  const flagsArray = Array.from(statusFlags);
  const parsedStatusDetails = parseStatusFlags(flagsArray);

  return {
    domain,
    source: 'whois',
    status,
    isAvailable: false,
    daysRemaining,
    registrar: {
      name: registrarName || 'Not Disclosed / Privacy Proxy',
      ianaId: registrarIanaId || null,
      url: registrarUrl || null,
      email: registrarEmail || null,
    },
    createdDate: createdDate ? createdDate.toISOString() : null,
    expiresDate: expiresDate ? expiresDate.toISOString() : null,
    updatedDate: updatedDate ? updatedDate.toISOString() : null,
    nameServers: Array.from(nameServers),
    statusFlags: flagsArray,
    parsedStatusDetails,
    dnssec,
    privacyProtected,
    registrantOrg: registrantOrg || (privacyProtected ? 'REDACTED FOR PRIVACY' : null),
    rawResponse: whoisText,
  };
}

/**
 * Flexible date parser for various registry date formats
 */
function parseFlexibleDate(dateStr) {
  if (!dateStr) return null;
  const cleanedStr = dateStr.replace(/#.*$/, '').trim();
  const d = new Date(cleanedStr);
  if (!isNaN(d.getTime())) {
    return d;
  }
  return null;
}

/**
 * Main query function orchestrating WHOIS lookup over TCP with referral tracking.
 * @param {string} domain
 * @param {string} primaryWhoisServer
 * @param {number} timeoutMs
 * @returns {Promise<object>}
 */
async function queryWhois(domain, primaryWhoisServer, timeoutMs = 8000) {
  let server = primaryWhoisServer || `whois.nic.${domain.split('.').pop()}`;
  let primaryText = '';

  try {
    primaryText = await sendTcpWhoisQuery(domain, server, timeoutMs);
  } catch (err) {
    // If primary server failed, attempt fallback to common default for TLD
    console.warn(`[WHOIS Client] Primary server ${server} failed: ${err.message}`);
    throw err;
  }

  // Check for 1-hop registrar referral
  const referralServer = extractReferralWhoisServer(primaryText);
  if (referralServer && referralServer !== server) {
    try {
      const referralText = await sendTcpWhoisQuery(domain, referralServer, timeoutMs);
      if (referralText && referralText.trim().length > 50) {
        // Merge responses or parse referral text
        const mergedText = `${primaryText}\n\n--- REGISTRAR REFERRAL WHOIS (${referralServer}) ---\n\n${referralText}`;
        return parseWhoisText(mergedText, domain);
      }
    } catch (referralErr) {
      console.warn(`[WHOIS Client] Referral query to ${referralServer} failed: ${referralErr.message}. Using primary response.`);
    }
  }

  return parseWhoisText(primaryText, domain);
}

module.exports = {
  queryWhois,
  sendTcpWhoisQuery,
  parseWhoisText,
  extractReferralWhoisServer,
};
