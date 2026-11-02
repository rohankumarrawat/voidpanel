const { parseAndValidateInput } = require('../src/utils/validation');

describe('Input Validation Utility', () => {
  test('should validate standard domain host and default to port 443', () => {
    const res = parseAndValidateInput('example.com');
    expect(res.isValid).toBe(true);
    expect(res.host).toBe('example.com');
    expect(res.port).toBe(443);
  });

  test('should parse shorthand host:port string', () => {
    const res = parseAndValidateInput('example.com:8443');
    expect(res.isValid).toBe(true);
    expect(res.host).toBe('example.com');
    expect(res.port).toBe(8443);
  });

  test('should strip https:// and trailing paths', () => {
    const res = parseAndValidateInput('https://google.com/search?q=test');
    expect(res.isValid).toBe(true);
    expect(res.host).toBe('google.com');
    expect(res.port).toBe(443);
  });

  test('should validate IPv4 address', () => {
    const res = parseAndValidateInput('1.1.1.1', 8443);
    expect(res.isValid).toBe(true);
    expect(res.host).toBe('1.1.1.1');
    expect(res.port).toBe(8443);
    expect(res.isIP).toBe(true);
  });

  test('should reject empty host input', () => {
    const res = parseAndValidateInput('');
    expect(res.isValid).toBe(false);
    expect(res.error).toBe('Host is required');
  });

  test('should reject invalid hostname format', () => {
    const res = parseAndValidateInput('not_a_valid_hostname!!!');
    expect(res.isValid).toBe(false);
    expect(res.error).toContain('Invalid hostname or IP');
  });

  test('should reject out of range port', () => {
    const res = parseAndValidateInput('example.com', 99999);
    expect(res.isValid).toBe(false);
    expect(res.error).toContain('Port must be an integer');
  });
});
