import test from 'node:test';
import assert from 'node:assert/strict';
import { parseDkimRecord } from '../server/services/dnsAnalyzer.js';

test('parseDkimRecord: parses valid RSA DKIM record', () => {
  const dkim = 'v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQD2AbCdEfGhIjKlMnOpQrStUvWxYz; h=sha256';
  const result = parseDkimRecord(dkim);

  assert.equal(result.found, true);
  assert.equal(result.valid, true);
  assert.equal(result.keyType, 'rsa');
  assert.equal(result.revoked, false);
  assert.equal(result.issues.length, 0);
});

test('parseDkimRecord: flags revoked key when p= is empty', () => {
  const dkim = 'v=DKIM1; k=rsa; p=';
  const result = parseDkimRecord(dkim);

  assert.equal(result.found, true);
  assert.equal(result.valid, false);
  assert.equal(result.revoked, true);
  assert.equal(result.issues.some((i) => i.includes('REVOKED')), true);
});

test('parseDkimRecord: handles empty input', () => {
  const result = parseDkimRecord('');

  assert.equal(result.found, false);
  assert.equal(result.valid, false);
  assert.equal(result.issues.length, 1);
});
