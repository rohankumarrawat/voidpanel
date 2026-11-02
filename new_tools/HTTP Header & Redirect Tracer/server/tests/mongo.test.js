const { Scan } = require('../db/mongo');

describe('MongoDB Compass Integration & Scan Schema', () => {
  test('Scan model creates valid scan document structure', async () => {
    const mockDoc = new Scan({
      inputUrl: 'http://testdomain.com',
      finalUrl: 'https://www.testdomain.com/',
      totalHops: 2,
      totalTimeMs: 180,
      securityScore: 92,
      securityGrade: 'A+',
      finalStatusCode: 200,
      finalStatusText: 'OK',
      chain: [
        { hop: 1, statusCode: 301, url: 'http://testdomain.com' },
        { hop: 2, statusCode: 200, url: 'https://www.testdomain.com/' }
      ],
      securityAudit: { score: 92, grade: 'A+' }
    });

    let validateErr = null;
    try {
      await mockDoc.validate();
    } catch (err) {
      validateErr = err;
    }

    expect(validateErr).toBeNull();
    expect(mockDoc.inputUrl).toBe('http://testdomain.com');
    expect(mockDoc.securityScore).toBe(92);
    expect(mockDoc.chain.length).toBe(2);
  });

  test('Scan model requires inputUrl field', async () => {
    const invalidDoc = new Scan({
      finalUrl: 'http://test.com'
    });

    let validateErr = null;
    try {
      await invalidDoc.validate();
    } catch (err) {
      validateErr = err;
    }

    expect(validateErr).not.toBeNull();
    expect(validateErr.errors.inputUrl).toBeDefined();
  });
});
