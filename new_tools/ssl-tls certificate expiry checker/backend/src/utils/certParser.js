const crypto = require('crypto');

/**
 * Helper to safely extract string or join array of strings (e.g. for OU or O fields)
 */
function formatStringOrArray(val, fallback = undefined) {
  if (!val) return fallback;
  if (Array.isArray(val)) return val.join(', ');
  return String(val);
}

/**
 * Checks if a hostname matches a SAN or Common Name (supporting wildcard certificates like *.example.com)
 */
function checkHostnameMatch(host, pattern) {
  if (!host || !pattern) return false;

  const h = host.toLowerCase().trim();
  const p = pattern.toLowerCase().trim();

  // Exact match
  if (h === p) return true;

  // Wildcard match e.g. *.example.com matching sub.example.com
  if (p.startsWith('*.')) {
    const domainSuffix = p.slice(2);
    const hostParts = h.split('.');
    const suffixParts = domainSuffix.split('.');

    if (hostParts.length === suffixParts.length + 1) {
      const hostSuffix = hostParts.slice(1).join('.');
      return hostSuffix === domainSuffix;
    }
  }

  return false;
}

/**
 * Parses Subject Alternative Names string into a structured array
 */
function parseSans(subjectAltNameStr) {
  if (!subjectAltNameStr || typeof subjectAltNameStr !== 'string') {
    return [];
  }

  return subjectAltNameStr
    .split(',')
    .map((item) => {
      const trimmed = item.trim();
      if (trimmed.startsWith('DNS:')) return trimmed.substring(4);
      if (trimmed.startsWith('IP Address:')) return trimmed.substring(11);
      if (trimmed.includes(':')) return trimmed.split(':')[1];
      return trimmed;
    })
    .filter((san) => san.length > 0);
}

/**
 * Formats raw SHA-256 fingerprint into colon-separated hex format
 */
function calculateSha256Fingerprint(cert) {
  if (cert.fingerprint256) {
    return cert.fingerprint256.toUpperCase();
  }
  if (cert.raw) {
    const hash = crypto.createHash('sha256').update(cert.raw).digest('hex');
    return hash.match(/.{2}/g).join(':').toUpperCase();
  }
  return 'N/A';
}

/**
 * Traverses certificate chain to construct issuer hierarchy
 */
function extractCertChain(leafCert) {
  const chain = [];
  let current = leafCert;
  let depth = 0;

  // Traverse certificate chain via issuerCertificate property up to 5 levels
  while (current && depth < 5) {
    const isLeaf = depth === 0;
    const isSelfSigned = current.issuer && current.subject &&
      formatStringOrArray(current.issuer.CN) === formatStringOrArray(current.subject.CN) &&
      formatStringOrArray(current.issuer.O) === formatStringOrArray(current.subject.O);

    chain.push({
      depth,
      type: isLeaf ? 'leaf' : isSelfSigned ? 'root' : 'intermediate',
      subject: {
        cn: formatStringOrArray(current.subject?.CN, 'N/A'),
        o: formatStringOrArray(current.subject?.O, 'N/A'),
        ou: formatStringOrArray(current.subject?.OU),
      },
      issuer: {
        cn: formatStringOrArray(current.issuer?.CN, 'N/A'),
        o: formatStringOrArray(current.issuer?.O, 'N/A'),
      },
      validFrom: current.valid_from ? new Date(current.valid_from).toISOString() : null,
      validTo: current.valid_to ? new Date(current.valid_to).toISOString() : null,
      serialNumber: current.serialNumber || 'N/A',
      fingerprintSha256: current.fingerprint256 || null,
    });

    if (current.issuerCertificate && current.issuerCertificate !== current) {
      current = current.issuerCertificate;
      depth += 1;
    } else {
      break;
    }
  }

  return chain;
}

/**
 * Main certificate parsing & validation entry point
 */
function parseCertificate(cert, targetHost, isAuthorized = true, authorizationError = null) {
  if (!cert || Object.keys(cert).length === 0) {
    return {
      status: 'error',
      statusReason: 'No SSL/TLS certificate was presented by target server.',
      isValid: false,
    };
  }

  const now = new Date();
  const notBefore = cert.valid_from ? new Date(cert.valid_from) : new Date();
  const notAfter = cert.valid_to ? new Date(cert.valid_to) : new Date();

  // Calculate days remaining (floor to whole days)
  const msDiff = notAfter.getTime() - now.getTime();
  const daysRemaining = Math.floor(msDiff / (1000 * 60 * 60 * 24));

  // Extract SANs & check hostname matching
  const sans = parseSans(cert.subjectaltname);
  const allNames = sans.length > 0 ? sans : [formatStringOrArray(cert.subject?.CN)].filter(Boolean);
  const hostnameMatch = allNames.some((name) => checkHostnameMatch(targetHost, name));

  // Key details
  let keySize = cert.bits || null;
  let keyAlgorithm = 'Unknown';
  if (cert.asn1Curve) {
    keyAlgorithm = `EC (${cert.asn1Curve})`;
  } else if (cert.bits) {
    keyAlgorithm = `RSA (${cert.bits}-bit)`;
  }

  // Determine certificate validity status
  let status = 'valid';
  let statusReason = 'Certificate is valid, trusted, and correctly matches hostname.';

  if (now > notAfter) {
    status = 'expired';
    statusReason = `Certificate expired on ${notAfter.toUTCString()} (${Math.abs(daysRemaining)} days ago).`;
  } else if (now < notBefore) {
    status = 'untrusted';
    statusReason = `Certificate is not yet valid (valid from ${notBefore.toUTCString()}).`;
  } else if (!isAuthorized) {
    status = 'untrusted';
    statusReason = `Untrusted certificate chain: ${authorizationError || 'Self-signed or missing root CA'}.`;
  } else if (!hostnameMatch) {
    status = 'untrusted';
    statusReason = `Hostname mismatch: '${targetHost}' does not match certificate SANs (${allNames.slice(0, 3).join(', ')}).`;
  } else if (daysRemaining <= 30) {
    status = 'expiring';
    statusReason = `Warning: Certificate expires in ${daysRemaining} day(s). Action recommended soon.`;
  }

  const fingerprintSha256 = calculateSha256Fingerprint(cert);
  const chain = extractCertChain(cert);

  return {
    host: targetHost,
    status,
    statusReason,
    isAuthorized,
    authorizationError: authorizationError || null,
    hostnameMatch,
    daysRemaining,
    validity: {
      notBefore: notBefore.toISOString(),
      notAfter: notAfter.toISOString(),
      isExpired: now > notAfter,
      isNotYetValid: now < notBefore,
    },
    subject: {
      cn: formatStringOrArray(cert.subject?.CN, 'N/A'),
      o: formatStringOrArray(cert.subject?.O, 'N/A'),
      ou: formatStringOrArray(cert.subject?.OU),
      c: formatStringOrArray(cert.subject?.C),
      st: formatStringOrArray(cert.subject?.ST),
      l: formatStringOrArray(cert.subject?.L),
    },
    issuer: {
      cn: formatStringOrArray(cert.issuer?.CN, 'N/A'),
      o: formatStringOrArray(cert.issuer?.O, 'N/A'),
      ou: formatStringOrArray(cert.issuer?.OU),
      c: formatStringOrArray(cert.issuer?.C),
    },
    sans,
    serialNumber: cert.serialNumber || 'N/A',
    fingerprintSha256,
    publicKey: {
      algorithm: keyAlgorithm,
      bits: keySize,
      asn1Curve: cert.asn1Curve || null,
    },
    signatureAlgorithm: cert.sigalg || 'sha256WithRSAEncryption',
    chainDepth: chain.length,
    certChain: chain,
    rawCertPem: cert.raw ? `-----BEGIN CERTIFICATE-----\n${cert.raw.toString('base64').match(/.{1,64}/g).join('\n')}\n-----END CERTIFICATE-----` : null,
  };
}

module.exports = {
  parseCertificate,
  parseSans,
  checkHostnameMatch,
  calculateSha256Fingerprint,
  extractCertChain,
};
