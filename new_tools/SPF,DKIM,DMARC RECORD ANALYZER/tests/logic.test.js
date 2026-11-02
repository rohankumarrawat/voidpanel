import test from 'node:test';
import assert from 'node:assert/strict';

import {
  parseSpfMechanisms,
  parseDkimRecord,
  parseDmarcRecord,
} from '../server/services/dnsAnalyzer.js';
import { normalizeDomainInput } from '../server/utils/domainValidator.js';

test('normalizeDomainInput handles domain and IP inputs', () => {
  assert.equal(normalizeDomainInput('example.com'), 'example.com');
  assert.equal(normalizeDomainInput('127.0.0.1'), '127.0.0.1');
  assert.equal(normalizeDomainInput('exämple.com'), 'xn--exmple-cua.com');
});

test('parseSpfMechanisms identifies terminal all qualifier', () => {
  const result = parseSpfMechanisms('v=spf1 include:_spf.example.com ip4:192.0.2.0/24 -all');
  assert.equal(result.terminalQualifier, '-all');
  assert.equal(result.mechanisms.length, 2);
});

test('parseDkimRecord reads key metadata', () => {
  const result = parseDkimRecord('v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC8; h=sha256');
  assert.equal(result.keyType, 'rsa');
  assert.equal(result.revoked, false);
});

test('parseDmarcRecord reads policy and alignment modes', () => {
  const result = parseDmarcRecord('v=DMARC1; p=quarantine; rua=mailto:admin@example.com; adkim=r; aspf=s');
  assert.equal(result.policy, 'quarantine');
  assert.equal(result.alignment.dkim, 'relaxed');
  assert.equal(result.alignment.spf, 'strict');
});
