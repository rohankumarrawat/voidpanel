import net from 'node:net';
import { domainToASCII } from 'node:url';

export function normalizeDomainInput(value) {
  if (!value || typeof value !== 'string') return '';

  let trimmed = value.trim().toLowerCase();
  // Strip http:// or https:// or mailto: if pasted
  trimmed = trimmed.replace(/^(?:https?:\/\/|mailto:)/i, '');
  // Strip trailing slashes or path/port
  trimmed = trimmed.split('/')[0].split(':')[0];

  if (!trimmed) return '';

  if (net.isIP(trimmed)) {
    return trimmed;
  }

  // Convert internationalized domain names (IDN) to ASCII / Punycode (e.g. exämple.com -> xn--exmple-cua.com)
  try {
    const asciiDomain = domainToASCII(trimmed);
    return asciiDomain || trimmed;
  } catch {
    return trimmed;
  }
}

export function validateDomainOrIp(value) {
  const normalized = normalizeDomainInput(value);
  if (!normalized) {
    return { valid: false, message: 'Please provide a valid domain name or IP address.' };
  }

  if (net.isIP(normalized)) {
    return { valid: true, value: normalized, isIp: true };
  }

  // Hostname regex compliant with RFC 1035 / RFC 1123
  const domainPattern = /^(?=.{1,253}$)(?!-)(?:[a-zA-Z0-9-]{1,63}\.)+[a-zA-Z]{2,63}$/;
  
  if (domainPattern.test(normalized) || /^xn--[a-zA-Z0-9-]+\.[a-zA-Z0-9.-]+$/.test(normalized)) {
    return { valid: true, value: normalized, isIp: false };
  }

  return {
    valid: false,
    message: 'Invalid domain format. Example valid domains: example.com, mail.google.com, 1.1.1.1',
  };
}
