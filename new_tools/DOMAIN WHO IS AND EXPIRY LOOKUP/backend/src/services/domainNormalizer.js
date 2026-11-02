const punycode = require('punycode/');

// IPv4 regex pattern
const IPV4_REGEX = /^(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;

// IPv6 regex pattern
const IPV6_REGEX = /^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$|^::(?:[0-9a-fA-F]{1,4}:){0,5}[0-9a-fA-F]{1,4}$|^[0-9a-fA-F]{1,4}::(?:[0-9a-fA-F]{1,4}:){0,4}[0-9a-fA-F]{1,4}$/;

// Standard domain regex pattern
const DOMAIN_REGEX = /^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$/;

/**
 * Normalizes and validates domain input.
 * @param {string} rawInput
 * @returns {object} { isValid, domain, asciiDomain, tld, error }
 */
function normalizeDomain(rawInput) {
  if (!rawInput || typeof rawInput !== 'string') {
    return {
      isValid: false,
      error: 'Please enter a valid domain name.',
    };
  }

  let cleaned = rawInput.trim();

  // Strip protocol (http://, https://, ftp://, etc.)
  cleaned = cleaned.replace(/^[a-zA-Z]+:\/\//, '');

  // Strip paths, query parameters, trailing slashes, auth credentials
  cleaned = cleaned.split('/')[0];
  cleaned = cleaned.split('?')[0];
  cleaned = cleaned.split('#')[0];

  // Strip brackets from IPv6 if present [2001:db8::1]:8080 -> 2001:db8::1
  let ipCheck = cleaned.replace(/^\[|\](?::\d+)?$/g, '');
  // Remove port for IPv6 if format is [2001:db8::1]:8080
  if (ipCheck.includes(':')) {
    ipCheck = ipCheck.split(']:')[0].replace(/^\[/, '');
  }

  // Check if input is IPv4 or IPv6
  if (IPV4_REGEX.test(cleaned.split(':')[0]) || IPV6_REGEX.test(ipCheck) || IPV6_REGEX.test(cleaned)) {
    return {
      isValid: false,
      error: 'IP address provided. WHOIS lookup is for domain names only. Please use the RBL/IP Checker tool for IP queries.',
    };
  }

  // Remove port number if any for domains (e.g. domain.com:8080)
  cleaned = cleaned.split(':')[0];

  // Strip leading/trailing whitespaces and dots
  cleaned = cleaned.replace(/^\.+|\.+$/g, '').toLowerCase();

  // Strip leading 'www.' if present for clean root domain lookup
  if (cleaned.startsWith('www.')) {
    cleaned = cleaned.substring(4);
  }

  if (!cleaned) {
    return {
      isValid: false,
      error: 'Please enter a valid domain name.',
    };
  }

  // Convert Unicode / IDN to Punycode
  let asciiDomain = cleaned;
  try {
    asciiDomain = punycode.toASCII(cleaned);
  } catch (err) {
    return {
      isValid: false,
      error: 'Invalid Internationalized Domain Name (IDN) encoding.',
    };
  }

  // Validate syntax
  if (!DOMAIN_REGEX.test(asciiDomain)) {
    return {
      isValid: false,
      error: 'Invalid domain syntax. Examples: voidonyx.in, voidpanel.com, github.com',
    };
  }

  // Extract TLD (e.g. .com, .in, .co.uk -> uk/co.uk)
  const parts = asciiDomain.split('.');
  if (parts.length < 2) {
    return {
      isValid: false,
      error: 'Domain must include a valid Top-Level Domain (TLD) extension like .com or .in',
    };
  }

  const tld = parts[parts.length - 1];

  return {
    isValid: true,
    domain: cleaned,
    asciiDomain: asciiDomain,
    tld: tld,
  };
}

module.exports = { normalizeDomain };
