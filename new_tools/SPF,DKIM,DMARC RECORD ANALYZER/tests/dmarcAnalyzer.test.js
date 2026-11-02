import test from 'node:test';
import assert from 'node:assert/strict';
import { parseDmarcRecord } from '../server/services/dnsAnalyzer.js';

test('parseDmarcRecord: correctly parses policy, percentage, and alignment tags', () => {
  const dmarc = 'v=DMARC1; p=reject; sp=quarantine; pct=100; adkim=s; aspf=r; rua=mailto:dmarc-reports@example.com';
  const result = parseDmarcRecord(dmarc);

  assert.equal(result.found, true);
  assert.equal(result.policy, 'reject');
  assert.equal(result.subdomainPolicy, 'quarantine');
  assert.equal(result.pct, 100);
  assert.equal(result.alignment.dkim, 'strict');
  assert.equal(result.alignment.spf, 'relaxed');
  assert.equal(result.rua.length, 1);
  assert.equal(result.rua[0], 'mailto:dmarc-reports@example.com');
});

test('parseDmarcRecord: flags p=none monitoring mode warning', () => {
  const dmarc = 'v=DMARC1; p=none; rua=mailto:dmarc@example.com';
  const result = parseDmarcRecord(dmarc);

  assert.equal(result.policy, 'none');
  assert.equal(result.issues.some((i) => i.includes('p=none')), true);
});

test('parseDmarcRecord: flags missing rua= reporting URI', () => {
  const dmarc = 'v=DMARC1; p=reject';
  const result = parseDmarcRecord(dmarc);

  assert.equal(result.rua.length, 0);
  assert.equal(result.issues.some((i) => i.includes('No aggregate report URI')), true);
});

test('parseDmarcRecord: handles missing DMARC record gracefully', () => {
  const result = parseDmarcRecord('');

  assert.equal(result.found, false);
  assert.equal(result.valid, false);
  assert.equal(result.policy, 'none');
  assert.equal(result.issues[0], 'No DMARC record found at _dmarc.<domain>.');
});
