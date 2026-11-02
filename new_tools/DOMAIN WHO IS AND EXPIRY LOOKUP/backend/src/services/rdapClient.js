const axios = require('axios');
const { parseStatusFlags } = require('./statusParser');

/**
 * Queries an RDAP base URL for domain information.
 * @param {string} domain - Normalized ASCII domain name
 * @param {Array<string>} rdapBaseUrls - Array of RDAP base URLs
 * @param {number} timeoutMs
 * @returns {Promise<object|null>} Parsed normalized object or null if failed/not supported
 */
async function queryRdap(domain, rdapBaseUrls = [], timeoutMs = 8000) {
  if (!rdapBaseUrls || rdapBaseUrls.length === 0) return null;

  for (let baseUrl of rdapBaseUrls) {
    if (!baseUrl.endsWith('/')) baseUrl += '/';
    const targetUrl = `${baseUrl}domain/${encodeURIComponent(domain)}`;

    try {
      const response = await axios.get(targetUrl, {
        timeout: timeoutMs,
        headers: {
          Accept: 'application/rdap+json, application/json',
          'User-Agent': 'VoidOnyx-WHOIS-RDAP-Lookup/1.0',
        },
      });

      if (response.data) {
        return parseRdapResponse(response.data, domain);
      }
    } catch (err) {
      if (err.response && err.response.status === 404) {
        // Domain is not registered (Available)
        return {
          domain,
          status: 'available',
          isAvailable: true,
          source: 'rdap',
          rawResponse: err.response.data || { status: 404, message: 'Domain not found in RDAP registry' },
        };
      }
      // If endpoint fails, try next baseUrl if available
    }
  }

  return null;
}

/**
 * Parses raw RDAP JSON into standard normalized schema
 */
function parseRdapResponse(rdapData, domain) {
  let createdDate = null;
  let expiresDate = null;
  let updatedDate = null;

  // Extract dates from 'events' array
  if (Array.isArray(rdapData.events)) {
    for (const event of rdapData.events) {
      if (!event.eventAction || !event.eventDate) continue;
      const action = event.eventAction.toLowerCase();
      const date = new Date(event.eventDate);

      if (action.includes('registration')) createdDate = date;
      else if (action.includes('expiration')) expiresDate = date;
      else if (action.includes('last changed') || action.includes('last update')) updatedDate = date;
    }
  }

  // Extract Registrar Name & IANA ID
  let registrarName = null;
  let registrarIanaId = null;
  let registrarUrl = null;
  let registrarEmail = null;
  let registrantOrg = null;
  let privacyProtected = false;

  if (Array.isArray(rdapData.entities)) {
    for (const entity of rdapData.entities) {
      const roles = (entity.roles || []).map((r) => r.toLowerCase());

      if (roles.includes('registrar')) {
        // Registrar entity
        if (entity.vcardArray && Array.isArray(entity.vcardArray[1])) {
          for (const item of entity.vcardArray[1]) {
            if (item[0] === 'fn') registrarName = item[3];
            else if (item[0] === 'email') registrarEmail = item[3];
            else if (item[0] === 'url') registrarUrl = item[3];
          }
        }
        if (entity.publicIds && Array.isArray(entity.publicIds)) {
          const iana = entity.publicIds.find((id) => id.type && id.type.toLowerCase().includes('iana'));
          if (iana) registrarIanaId = iana.identifier;
        }
      }

      if (roles.includes('registrant')) {
        if (entity.vcardArray && Array.isArray(entity.vcardArray[1])) {
          for (const item of entity.vcardArray[1]) {
            if (item[0] === 'org' || item[0] === 'fn') {
              const val = item[3];
              if (val && (val.toLowerCase().includes('redacted') || val.toLowerCase().includes('privacy') || val.toLowerCase().includes('proxy'))) {
                privacyProtected = true;
              } else {
                registrantOrg = val;
              }
            }
          }
        }
      }

      // Check remarks for privacy redaction notice
      if (Array.isArray(entity.remarks)) {
        for (const remark of entity.remarks) {
          if (remark.title && remark.title.toLowerCase().includes('redacted')) {
            privacyProtected = true;
          }
        }
      }
    }
  }

  // Check top-level remarks for redaction notices
  if (Array.isArray(rdapData.remarks)) {
    for (const remark of rdapData.remarks) {
      const text = `${remark.title || ''} ${(remark.description || []).join(' ')}`.toLowerCase();
      if (text.includes('redacted for privacy') || text.includes('gdpr')) {
        privacyProtected = true;
      }
    }
  }

  // Extract Name Servers
  const nameServers = [];
  if (Array.isArray(rdapData.nameservers)) {
    for (const ns of rdapData.nameservers) {
      if (ns.ldhName) nameServers.push(ns.ldhName.toLowerCase());
    }
  }

  // Extract Domain Status Flags
  const statusFlags = Array.isArray(rdapData.status) ? rdapData.status : [];
  const parsedStatusDetails = parseStatusFlags(statusFlags);

  // Extract DNSSEC Status
  let dnssec = 'unsigned';
  if (rdapData.secureDNS && rdapData.secureDNS.delegationSigned) {
    dnssec = 'signed';
  }

  // Days remaining calculation
  let daysRemaining = null;
  let status = 'active';

  if (expiresDate && !isNaN(expiresDate.getTime())) {
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

  return {
    domain,
    source: 'rdap',
    status,
    isAvailable: false,
    daysRemaining,
    registrar: {
      name: registrarName || 'Not Disclosed / Privacy Proxy',
      ianaId: registrarIanaId ? String(registrarIanaId) : null,
      url: registrarUrl,
      email: registrarEmail,
    },
    createdDate: createdDate && !isNaN(createdDate.getTime()) ? createdDate.toISOString() : null,
    expiresDate: expiresDate && !isNaN(expiresDate.getTime()) ? expiresDate.toISOString() : null,
    updatedDate: updatedDate && !isNaN(updatedDate.getTime()) ? updatedDate.toISOString() : null,
    nameServers,
    statusFlags,
    parsedStatusDetails,
    dnssec,
    privacyProtected,
    registrantOrg: registrantOrg || (privacyProtected ? 'REDACTED FOR PRIVACY' : null),
    rawResponse: rdapData,
  };
}

module.exports = { queryRdap, parseRdapResponse };
