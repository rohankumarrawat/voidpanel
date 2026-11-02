const API_BASE_URL = import.meta.env.VITE_API_URL || '';

/**
 * Perform certificate inspection API call
 */
export async function checkCertificate(host, port = 443) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/check`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ host, port }),
    });

    const data = await response.json();

    if (!response.ok) {
      return {
        success: false,
        status: response.status,
        code: data.code || 'API_ERROR',
        error: data.error || 'Check failed',
        message: data.message || 'An error occurred while inspecting the certificate.',
        resetInSeconds: data.resetInSeconds || null,
      };
    }

    return {
      success: true,
      data,
    };
  } catch (err) {
    return {
      success: false,
      status: 0,
      code: 'NETWORK_ERROR',
      error: 'Network Error',
      message: 'Unable to communicate with VoidOnyX API backend. Please ensure backend service is running.',
    };
  }
}

/**
 * Fetch recent public checks feed
 */
export async function fetchRecentChecks() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/recent`);
    if (!response.ok) return [];
    const data = await response.json();
    return data.recent || [];
  } catch (err) {
    return [];
  }
}
