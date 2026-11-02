const {
  parseCertificate,
  parseSans,
  checkHostnameMatch,
  calculateSha256Fingerprint,
} = require('../src/utils/certParser');

describe('Certificate Parser Utility', () => {
  test('should correctly parse SAN string into clean array', () => {
    const rawSans = 'DNS:example.com, DNS:*.example.com, IP Address:1.1.1.1';
    const parsed = parseSans(rawSans);
    expect(parsed).toEqual(['example.com', '*.example.com', '1.1.1.1']);
  });

  test('should match hostname against exact and wildcard SANs', () => {
    expect(checkHostnameMatch('example.com', 'example.com')).toBe(true);
    expect(checkHostnameMatch('sub.example.com', '*.example.com')).toBe(true);
    expect(checkHostnameMatch('deep.sub.example.com', '*.example.com')).toBe(false);
    expect(checkHostnameMatch('other.com', 'example.com')).toBe(false);
  });

  test('should flag expired certificate status correctly', () => {
    const pastDate = new Date(Date.now() - 86400000 * 5).toUTCString(); // 5 days ago
    const oldStartDate = new Date(Date.now() - 86400000 * 365).toUTCString();

    const mockCert = {
      subject: { CN: 'expired.example.com', O: 'Test Corp' },
      issuer: { CN: 'Test CA', O: 'Test CA Org' },
      valid_from: oldStartDate,
      valid_to: pastDate,
      subjectaltname: 'DNS:expired.example.com',
      bits: 2048,
      fingerprint256: 'AA:BB:CC:DD',
    };

    const parsed = parseCertificate(mockCert, 'expired.example.com', true, null);
    expect(parsed.status).toBe('expired');
    expect(parsed.daysRemaining).toBeLessThan(0);
    expect(parsed.validity.isExpired).toBe(true);
  });

  test('should flag expiring certificate status when <= 30 days remaining', () => {
    const futureDate = new Date(Date.now() + 86400000 * 10).toUTCString(); // 10 days from now
    const oldStartDate = new Date(Date.now() - 86400000 * 300).toUTCString();

    const mockCert = {
      subject: { CN: 'expiring.example.com' },
      issuer: { CN: 'Test CA' },
      valid_from: oldStartDate,
      valid_to: futureDate,
      subjectaltname: 'DNS:expiring.example.com',
      bits: 2048,
    };

    const parsed = parseCertificate(mockCert, 'expiring.example.com', true, null);
    expect(parsed.status).toBe('expiring');
    expect(parsed.daysRemaining).toBeGreaterThanOrEqual(9);
    expect(parsed.daysRemaining).toBeLessThanOrEqual(10);
  });

  test('should flag untrusted certificate when socket is unauthorized', () => {
    const futureDate = new Date(Date.now() + 86400000 * 100).toUTCString();
    const oldStartDate = new Date(Date.now() - 86400000 * 10).toUTCString();

    const mockCert = {
      subject: { CN: 'self-signed.local' },
      issuer: { CN: 'self-signed.local' },
      valid_from: oldStartDate,
      valid_to: futureDate,
      subjectaltname: 'DNS:self-signed.local',
      bits: 2048,
    };

    const parsed = parseCertificate(mockCert, 'self-signed.local', false, 'DEPTH_ZERO_SELF_SIGNED_CERT');
    expect(parsed.status).toBe('untrusted');
    expect(parsed.isAuthorized).toBe(false);
    expect(parsed.authorizationError).toBe('DEPTH_ZERO_SELF_SIGNED_CERT');
  });

  test('should calculate valid status for trusted cert with > 30 days remaining', () => {
    const futureDate = new Date(Date.now() + 86400000 * 90).toUTCString();
    const startDate = new Date(Date.now() - 86400000 * 10).toUTCString();

    const mockCert = {
      subject: { CN: 'secure.example.com', O: 'VoidOnyX' },
      issuer: { CN: 'Let\'s Encrypt Authority X3', O: 'Let\'s Encrypt' },
      valid_from: startDate,
      valid_to: futureDate,
      subjectaltname: 'DNS:secure.example.com',
      bits: 2048,
    };

    const parsed = parseCertificate(mockCert, 'secure.example.com', true, null);
    expect(parsed.status).toBe('valid');
    expect(parsed.daysRemaining).toBeGreaterThanOrEqual(89);
    expect(parsed.daysRemaining).toBeLessThanOrEqual(90);
    expect(parsed.subject.cn).toBe('secure.example.com');
    expect(parsed.issuer.cn).toBe('Let\'s Encrypt Authority X3');
  });
});
