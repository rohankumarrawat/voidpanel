export async function analyzeDomain(domain, selectors) {
  const response = await fetch('/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ domain, selectors }),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || 'Failed to analyze domain authentication posture.');
  }

  return data;
}

export async function fetchScanHistory(domain = '') {
  const url = domain ? `/api/history?domain=${encodeURIComponent(domain)}` : '/api/history';
  const response = await fetch(url);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || 'Failed to fetch scan history.');
  }
  return data.scans || [];
}

export async function fetchDefaultSelectors() {
  const response = await fetch('/api/default-selectors');
  const data = await response.json();
  return data.selectors || [];
}
