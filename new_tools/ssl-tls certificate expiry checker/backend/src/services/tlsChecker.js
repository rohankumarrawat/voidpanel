const tls = require('tls');
const net = require('net');
const env = require('../config/env');
const { parseCertificate } = require('../utils/certParser');

/**
 * Performs a TLS handshake to check TLS 1.2 compatibility specifically
 */
function checkTls12Support(host, port, timeoutMs) {
  return new Promise((resolve) => {
    let timer;
    const socket = tls.connect({
      host,
      port,
      servername: host,
      rejectUnauthorized: false,
      minVersion: 'TLSv1.2',
      maxVersion: 'TLSv1.2',
      timeout: timeoutMs,
    });

    const cleanup = () => {
      if (timer) clearTimeout(timer);
      if (!socket.destroyed) socket.destroy();
    };

    timer = setTimeout(() => {
      cleanup();
      resolve(false);
    }, timeoutMs);

    socket.on('secureConnect', () => {
      cleanup();
      resolve(true);
    });

    socket.on('error', () => {
      cleanup();
      resolve(false);
    });
  });
}

/**
 * Main TLS Inspection Engine
 */
function fetchCertificate(host, port = 443, timeoutMs = env.TLS_TIMEOUT_MS) {
  return new Promise((resolve, reject) => {
    let timer;
    let isHandshakeComplete = false;

    // Check pre-socket IP vs Host format
    const isIp = net.isIP(host);

    const socketOptions = {
      host,
      port,
      rejectUnauthorized: false, // Extract cert data even if untrusted/self-signed
      timeout: timeoutMs,
    };

    // Include SNI header for hostnames (skip for raw IP addresses)
    if (!isIp) {
      socketOptions.servername = host;
    }

    const socket = tls.connect(socketOptions);

    const cleanup = () => {
      if (timer) clearTimeout(timer);
      if (!socket.destroyed) socket.destroy();
    };

    timer = setTimeout(() => {
      if (!isHandshakeComplete) {
        cleanup();
        reject({
          code: 'ETIMEDOUT',
          message: `Connection timed out after ${timeoutMs / 1000}s while attempting TLS handshake with ${host}:${port}.`,
          userFriendly: `Host '${host}' on port ${port} took too long to respond.`,
        });
      }
    }, timeoutMs);

    socket.on('secureConnect', async () => {
      isHandshakeComplete = true;
      try {
        const peerCert = socket.getPeerCertificate(true);
        const isAuthorized = socket.authorized;
        const authorizationError = socket.authorizationError;
        const negotiatedProtocol = socket.getProtocol();

        if (!peerCert || Object.keys(peerCert).length === 0) {
          cleanup();
          return reject({
            code: 'ENOCERT',
            message: `No TLS certificate presented by ${host}:${port}.`,
            userFriendly: `Server at '${host}:${port}' did not provide a TLS certificate.`,
          });
        }

        // Parse extracted certificate
        const parsedCert = parseCertificate(peerCert, host, isAuthorized, authorizationError);

        // Perform secondary TLS 1.2 compatibility probe in parallel/quick fallback
        let tlsVersionsSupported = [negotiatedProtocol || 'TLSv1.3'];
        
        try {
          const supportsTls12 = await checkTls12Support(host, port, Math.min(3000, timeoutMs));
          if (supportsTls12 && !tlsVersionsSupported.includes('TLSv1.2')) {
            tlsVersionsSupported.push('TLSv1.2');
          }
        } catch (e) {
          // Ignore secondary probe failures
        }

        cleanup();
        resolve({
          host,
          port,
          protocol: negotiatedProtocol || 'TLSv1.3',
          tlsVersionsSupported,
          ...parsedCert,
          checkedAt: new Date().toISOString(),
        });
      } catch (err) {
        cleanup();
        reject({
          code: 'EPARSEFAILED',
          message: `Failed to parse certificate from ${host}:${port}: ${err.message}`,
          userFriendly: `Unable to process the security certificate from '${host}'.`,
        });
      }
    });

    socket.on('error', (err) => {
      if (isHandshakeComplete) return;
      cleanup();

      let userFriendly = `Failed to connect to '${host}' on port ${port}.`;
      if (err.code === 'ENOTFOUND') {
        userFriendly = `Domain '${host}' could not be resolved (DNS lookup failed).`;
      } else if (err.code === 'ECONNREFUSED') {
        userFriendly = `Connection refused by '${host}' on port ${port}. Ensure a TLS service is running on this port.`;
      } else if (err.code === 'EHOSTUNREACH' || err.code === 'ENETUNREACH') {
        userFriendly = `Host '${host}' is unreachable over the network.`;
      } else if (err.code === 'ERR_TLS_CERT_ALTNAME_INVALID') {
        userFriendly = `Hostname mismatch for '${host}'.`;
      } else if (err.message && err.message.includes('wrong version number')) {
        userFriendly = `Port ${port} does not appear to be running HTTPS/TLS service.`;
      }

      reject({
        code: err.code || 'ECONNFAILED',
        message: err.message,
        userFriendly,
      });
    });
  });
}

module.exports = { fetchCertificate, checkTls12Support };
