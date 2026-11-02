const validator = require('validator');

/**
 * Parses and validates host input (domain or IP, optional port)
 * Supports shorthand like "example.com:8443" or separate host/port parameters
 */
function parseAndValidateInput(rawHost, rawPort) {
  if (!rawHost || typeof rawHost !== 'string') {
    return { isValid: false, error: 'Host is required' };
  }

  let host = rawHost.trim().toLowerCase();
  let port = rawPort ? parseInt(rawPort, 10) : 443;

  // Remove protocol prefixes if user pasted http:// or https://
  if (host.startsWith('https://')) {
    host = host.slice(8);
  } else if (host.startsWith('http://')) {
    host = host.slice(7);
  }

  // Remove trailing slashes or URL paths
  const slashIndex = host.indexOf('/');
  if (slashIndex !== -1) {
    host = host.substring(0, slashIndex);
  }

  // Handle IPv6 bracket shorthand e.g. [::1]:8443 or host:port shorthand
  if (host.startsWith('[')) {
    const closingBracket = host.indexOf(']');
    if (closingBracket !== -1) {
      const ipv6Part = host.substring(1, closingBracket);
      const rest = host.substring(closingBracket + 1);
      host = ipv6Part;
      if (rest.startsWith(':')) {
        const parsedPort = parseInt(rest.substring(1), 10);
        if (!isNaN(parsedPort)) port = parsedPort;
      }
    }
  } else if (host.includes(':')) {
    const parts = host.split(':');
    // Only split if it's a domain/IPv4 with single colon for port (IPv6 has multiple colons)
    if (parts.length === 2) {
      host = parts[0];
      const parsedPort = parseInt(parts[1], 10);
      if (!isNaN(parsedPort)) {
        port = parsedPort;
      }
    }
  }

  // Validate port range
  if (isNaN(port) || port < 1 || port > 65535) {
    return { isValid: false, error: 'Port must be an integer between 1 and 65535' };
  }

  // Check if host is valid IPv4, IPv6, or domain name
  const isIP = validator.isIP(host);
  const isDomain = validator.isFQDN(host, { require_tld: false, allow_underscores: true }) || host === 'localhost';

  if (!isIP && !isDomain) {
    return { isValid: false, error: 'Invalid hostname or IP address format' };
  }

  return {
    isValid: true,
    host,
    port,
    isIP,
  };
}

module.exports = { parseAndValidateInput };
