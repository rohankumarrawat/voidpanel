const { normalizeDomain } = require('../src/services/domainNormalizer');

describe('Domain Normalizer Service', () => {
  test('normalizes standard domain inputs', () => {
    const res = normalizeDomain('https://www.voidonyx.in/some/path?query=1');
    expect(res.isValid).toBe(true);
    expect(res.domain).toBe('voidonyx.in');
    expect(res.tld).toBe('in');
  });

  test('converts Internationalized Domain Names (IDN) to Punycode', () => {
    const res = normalizeDomain('xn--bcher-kva.example');
    expect(res.isValid).toBe(true);
    expect(res.asciiDomain).toBe('xn--bcher-kva.example');
  });

  test('rejects IP addresses with explicit error message', () => {
    const resV4 = normalizeDomain('192.168.1.1');
    expect(resV4.isValid).toBe(false);
    expect(resV4.error).toContain('IP address provided');

    const resV6 = normalizeDomain('2001:0db8:85a3:0000:0000:8a2e:0370:7334');
    expect(resV6.isValid).toBe(false);
    expect(resV6.error).toContain('IP address provided');
  });

  test('rejects empty or malformed inputs', () => {
    expect(normalizeDomain('').isValid).toBe(false);
    expect(normalizeDomain('   ').isValid).toBe(false);
    expect(normalizeDomain('invalid_domain_name').isValid).toBe(false);
  });
});
