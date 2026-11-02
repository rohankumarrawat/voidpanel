import test from 'node:test';
import assert from 'node:assert/strict';
import { parseSpfMechanisms, calculateOverallScore } from '../server/services/dnsAnalyzer.js';

test('parseSpfMechanisms: identifies mechanisms and qualifiers correctly', () => {
  const spf = 'v=spf1 ip4:192.0.2.0/24 include:_spf.google.com ~all';
  const result = parseSpfMechanisms(spf);

  assert.equal(result.terminalQualifier, '~all');
  assert.equal(result.mechanisms.length, 2);
  assert.equal(result.mechanisms[0].type, 'ip4');
  assert.equal(result.mechanisms[1].type, 'include');
  assert.equal(result.mechanisms[1].target, '_spf.google.com');
  assert.equal(result.issues.length, 0);
});

test('parseSpfMechanisms: flags dangerous +all qualifier', () => {
  const spf = 'v=spf1 include:_spf.google.com +all';
  const result = parseSpfMechanisms(spf);

  assert.equal(result.terminalQualifier, '+all');
  assert.equal(result.issues.some((i) => i.includes('CRITICAL: "+all"')), true);
});

test('parseSpfMechanisms: flags missing terminal all qualifier', () => {
  const spf = 'v=spf1 ip4:198.51.100.1 include:example.org';
  const result = parseSpfMechanisms(spf);

  assert.equal(result.terminalQualifier, 'none');
  assert.equal(result.issues.some((i) => i.includes('WARNING: No terminal "all"')), true);
});

test('calculateOverallScore: outputs correct status tiers', () => {
  const goodSpf = { found: true, maxLookupsExceeded: false, terminalQualifier: '-all' };
  const goodDkim = { foundCount: 1 };
  const goodDmarc = { found: true, policy: 'reject' };

  assert.equal(calculateOverallScore(goodSpf, goodDkim, goodDmarc), 'Good');

  const warnDmarc = { found: true, policy: 'none' };
  assert.equal(calculateOverallScore(goodSpf, goodDkim, warnDmarc), 'Needs Improvement');

  const badSpf = { found: true, maxLookupsExceeded: true, terminalQualifier: '~all' };
  assert.equal(calculateOverallScore(badSpf, goodDkim, warnDmarc), 'Poor');
});
