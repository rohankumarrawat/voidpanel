const http = require('http');
const https = require('https');
const { URL } = require('url');
const ipaddr = require('ipaddr.js');
const validator = require('validator');
const { analyzeHeaders } = require('./securityHeaderAnalyzer');

// Checks if host or IP is private/local to prevent SSRF
function isPrivateHost(hostname, allowLocal = false) {
  if (allowLocal) return false;
  
  const lower = hostname.toLowerCase();
  if (lower === 'localhost' || lower.endsWith('.local') || lower.endsWith('.internal')) {
    return true;
  }

  // If IP address
  if (validator.isIP(lower)) {
    try {
      const addr = ipaddr.parse(lower);
      const range = addr.range();
      if (['loopback', 'private', 'linkLocal', 'uniqueLocal', 'carrierNat', 'unspecified'].includes(range)) {
        return true;
      }
    } catch (e) {
      return true;
    }
  }
  return false;
}

/**
 * Execute single HTTP/HTTPS request without following redirects automatically.
 */
function fetchSingleHop(targetUrl, timeoutMs = 10000, userAgent = 'HTTP-Header-Redirect-Tracer/1.0') {
  return new Promise((resolve, reject) => {
    let parsedUrl;
    try {
      parsedUrl = new URL(targetUrl);
    } catch (e) {
      return reject(new Error(`Invalid URL format: ${targetUrl}`));
    }

    const isSecure = parsedUrl.protocol === 'https:';
    const client = isSecure ? https : http;

    const requestOptions = {
      protocol: parsedUrl.protocol,
      hostname: parsedUrl.hostname,
      port: parsedUrl.port || (isSecure ? 443 : 80),
      path: `${parsedUrl.pathname}${parsedUrl.search}`,
      method: 'GET',
      headers: {
        'User-Agent': userAgent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'close'
      },
      timeout: timeoutMs
    };

    const startTime = Date.now();

    const req = client.request(requestOptions, (res) => {
      const duration = Date.now() - startTime;
      const headers = res.headers;
      const statusCode = res.statusCode;
      const statusText = res.statusMessage || http.STATUS_CODES[statusCode] || 'Unknown';
      const location = headers.location || null;

      // Clean up body stream without consuming large payload
      res.destroy();

      resolve({
        url: targetUrl,
        statusCode,
        statusText,
        location,
        responseTimeMs: duration,
        protocol: isSecure ? 'HTTPS' : 'HTTP',
        headers
      });
    });

    req.on('timeout', () => {
      req.destroy();
      reject(new Error(`Request timed out after ${timeoutMs}ms for ${targetUrl}`));
    });

    req.on('error', (err) => {
      reject(new Error(`Connection error for ${targetUrl}: ${err.message}`));
    });

    req.end();
  });
}

/**
 * Follow HTTP redirects iteratively up to maxHops
 */
async function traceRedirectChain(initialInput, options = {}) {
  const maxHops = options.maxHops || 10;
  const timeoutMs = options.timeoutMs || 10000;
  const allowLocal = options.allowLocal || false;
  const userAgent = options.userAgent || 'HTTP-Header-Redirect-Tracer/1.0';

  let currentUrl = initialInput.trim();
  if (!/^https?:\/\//i.test(currentUrl)) {
    currentUrl = 'http://' + currentUrl;
  }

  // Validate initial URL syntax
  try {
    new URL(currentUrl);
  } catch (err) {
    throw new Error(`Invalid URL specified: '${initialInput}'`);
  }

  const chain = [];
  const visitedUrls = new Set();
  let loopDetected = false;
  let maxHopsExceeded = false;

  const totalStartTime = Date.now();

  for (let hopIndex = 1; hopIndex <= maxHops; hopIndex++) {
    let parsedUrl;
    try {
      parsedUrl = new URL(currentUrl);
    } catch (e) {
      throw new Error(`Malformed URL encountered during redirect chain: ${currentUrl}`);
    }

    if (isPrivateHost(parsedUrl.hostname, allowLocal)) {
      throw new Error(`Access restricted: Destination '${parsedUrl.hostname}' resolves to a local or private network IP.`);
    }

    if (visitedUrls.has(currentUrl)) {
      loopDetected = true;
      break;
    }
    visitedUrls.add(currentUrl);

    let result;
    try {
      result = await fetchSingleHop(currentUrl, timeoutMs, userAgent);
    } catch (err) {
      chain.push({
        hop: hopIndex,
        url: currentUrl,
        statusCode: 0,
        statusText: 'ERR_CONNECTION_FAILED',
        error: err.message,
        location: null,
        responseTimeMs: 0,
        protocol: parsedUrl.protocol.replace(':', '').toUpperCase(),
        headers: {}
      });
      break;
    }

    const isRedirect = [301, 302, 303, 307, 308].includes(result.statusCode);

    chain.push({
      hop: hopIndex,
      url: currentUrl,
      statusCode: result.statusCode,
      statusText: result.statusText,
      location: result.location,
      responseTimeMs: result.responseTimeMs,
      protocol: result.protocol,
      headers: result.headers,
      isRedirect
    });

    if (isRedirect && result.location) {
      // Resolve relative location URLs against current hop URL
      try {
        currentUrl = new URL(result.location, currentUrl).href;
      } catch (e) {
        throw new Error(`Invalid Location header header '${result.location}' returned by ${currentUrl}`);
      }

      if (hopIndex === maxHops) {
        maxHopsExceeded = true;
      }
    } else {
      // Reached final destination or non-redirect status
      break;
    }
  }

  const totalTimeMs = Date.now() - totalStartTime;

  // Run security header audit on the final successful response hop (or last available hop)
  const finalHop = chain[chain.length - 1];
  const finalProtocol = finalHop ? (finalHop.protocol === 'HTTPS' ? 'https:' : 'http:') : 'http:';
  const securityAudit = analyzeHeaders(finalHop ? finalHop.headers : {}, finalProtocol);

  return {
    inputUrl: initialInput,
    startUrl: chain[0] ? chain[0].url : currentUrl,
    finalUrl: finalHop ? finalHop.url : currentUrl,
    totalHops: chain.length,
    totalTimeMs,
    loopDetected,
    maxHopsExceeded,
    chain,
    securityAudit
  };
}

module.exports = {
  traceRedirectChain,
  isPrivateHost
};
