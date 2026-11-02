const { parseWhoisText, extractReferralWhoisServer } = require('../src/services/whoisClient');

describe('WHOIS Text Parser Service', () => {
  const sampleStandardWhois = `
   Domain Name: VOIDPANEL.COM
   Registry Domain ID: 2634819201_DOMAIN_COM-VRSN
   Registrar WHOIS Server: whois.namecheap.com
   Registrar URL: http://www.namecheap.com
   Updated Date: 2025-05-10T12:00:00Z
   Creation Date: 2023-08-15T08:30:00Z
   Registry Expiry Date: 2028-08-15T08:30:00Z
   Registrar: NameCheap, Inc.
   Registrar IANA ID: 1068
   Domain Status: clientTransferProhibited https://icann.org/epp#clientTransferProhibited
   Name Server: NS1.VOIDONYX.IN
   Name Server: NS2.VOIDONYX.IN
   DNSSEC: unsigned
`;

  const sampleGdprWhois = `
   Domain Name: PRIVACY-TEST.COM
   Registrar: GoDaddy.com, LLC
   Creation Date: 2021-01-01T00:00:00Z
   Registry Expiry Date: 2029-01-01T00:00:00Z
   Registrant Organization: REDACTED FOR PRIVACY
   Registrant Name: REDACTED FOR PRIVACY
   Name Server: NS1.GODADDY.COM
   Name Server: NS2.GODADDY.COM
   DNSSEC: unsigned
`;

  const sampleAvailableWhois = `
   No match for domain "UNREGISTERED-DOMAIN-99999.COM".
   >>> Last update of WHOIS database: 2026-08-11T12:00:00Z <<<
`;

  test('parses standard WHOIS response', () => {
    const res = parseWhoisText(sampleStandardWhois, 'voidpanel.com');
    expect(res.isAvailable).toBe(false);
    expect(res.registrar.name).toBe('NameCheap, Inc.');
    expect(res.registrar.ianaId).toBe('1068');
    expect(res.nameServers).toContain('ns1.voidonyx.in');
    expect(res.nameServers).toContain('ns2.voidonyx.in');
    expect(res.statusFlags).toContain('clientTransferProhibited');
    expect(res.status).toBe('active');
  });

  test('detects GDPR privacy redaction without flagging as error', () => {
    const res = parseWhoisText(sampleGdprWhois, 'privacy-test.com');
    expect(res.isAvailable).toBe(false);
    expect(res.privacyProtected).toBe(true);
    expect(res.status).toBe('privacy_protected');
    expect(res.registrantOrg).toBe('REDACTED FOR PRIVACY');
  });

  test('detects available / unregistered domain state', () => {
    const res = parseWhoisText(sampleAvailableWhois, 'unregistered-domain-99999.com');
    expect(res.isAvailable).toBe(true);
    expect(res.status).toBe('available');
  });

  test('extracts referral WHOIS server correctly', () => {
    const referral = extractReferralWhoisServer(sampleStandardWhois);
    expect(referral).toBe('whois.namecheap.com');
  });
});
