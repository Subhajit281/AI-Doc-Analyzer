const configuredApiUrl = (
  import.meta.env.VITE_API_URL ||
  'https://ai-doc-analyzer-ccuv.onrender.com'
).trim();
const API_URL = (configuredApiUrl.startsWith('http')
  ? configuredApiUrl
  : `https://${configuredApiUrl}`
).replace(/\/+$/, '');
const REQUEST_TIMEOUT_MS = 45_000;

// ============================================================
// API ERROR
// ============================================================

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

function getAuthHeaders() {
  const token = localStorage.getItem('docai_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function apiFetch(url, options = {}, timeoutMs = REQUEST_TIMEOUT_MS) {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new ApiError('The request took too long. Please try again.', 408);
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}

async function responseJson(response, fallbackMessage) {
  try {
    return await response.json();
  } catch {
    throw new ApiError(fallbackMessage, response.status);
  }
}

// ============================================================
// UPLOAD DOCUMENT
// ============================================================

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append('file', file);

  let response;
  try {
    response = await apiFetch(`${API_URL}/documents/upload`, {
      method: 'POST',
      headers: {
        ...getAuthHeaders(),
      },
      body: formData,
    }, 120_000);
  } catch {
    throw new ApiError('Unable to upload the document. Please try again.', 0);
  }

  if (!response.ok) {
    let message = 'Unable to upload the document. Please try again.';
    try {
      const errorData = await response.json();
      if (typeof errorData.detail === 'string') {
        message = errorData.detail;
      }
    } catch {
      // Keep default error message
    }
    throw new ApiError(message, response.status);
  }

  try {
    return await response.json();
  } catch {
    throw new ApiError('Unable to upload the document. Please try again.', response.status);
  }
}

// ============================================================
// ASK QUESTION
// ============================================================

export async function askQuestion(documentId, query, conversationId) {
  if (!documentId || !documentId.trim()) {
    throw new ApiError('Document ID is required.', 400);
  }

  if (!query || !query.trim()) {
    throw new ApiError('Query cannot be empty.', 400);
  }

  if (!conversationId || !conversationId.trim()) {
    throw new ApiError('Conversation ID is required.', 400);
  }

  let response;
  try {
    response = await apiFetch(`${API_URL}/documents/${documentId}/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      body: JSON.stringify({
        query: query.trim(),
        conversation_id: conversationId.trim(),
      }),
    }, 90_000);
  } catch {
    throw new ApiError('Unable to get a response. Please check your connection.', 0);
  }

  if (!response.ok) {
    if (response.status === 402) {
      throw new ApiError('QUOTA_EXCEEDED', 402);
    }

    let message = 'Unable to get a response. Please try again.';
    try {
      const errorData = await response.json();
      if (typeof errorData.detail === 'string') {
        message = errorData.detail;
      } else if (Array.isArray(errorData.detail)) {
        message = errorData.detail.map((e) => e.msg || 'Invalid request.').join(', ');
      }
    } catch {
      // Keep default error message
    }

    throw new ApiError(message, response.status);
  }

  try {
    const data = await response.json();
    let answer = data.answer;

    if (typeof answer === 'string') {
      // Already string
    } else if (Array.isArray(answer)) {
      answer = answer
        .map((item) => {
          if (typeof item === 'string') return item;
          if (item && typeof item.text === 'string') return item.text;
          return '';
        })
        .filter(Boolean)
        .join('\n\n');
    } else if (answer && typeof answer.text === 'string') {
      answer = answer.text;
    } else {
      answer = String(answer ?? '');
    }

    return {
      ...data,
      answer,
    };
  } catch {
    throw new ApiError('Unable to parse response. Please try again.', response.status);
  }
}

// ============================================================
// DELETE DOCUMENT
// ============================================================

export async function getUserDocuments() {
  try {
    const response = await apiFetch(`${API_URL}/documents`, {
      headers: {
        ...getAuthHeaders(),
      },
    });

    if (!response.ok) {
      return [];
    }

    const data = await response.json();
    return data.documents || [];
  } catch (err) {
    console.warn('Failed to load user documents from DB:', err);
    return [];
  }
}

export async function deleteDocument(documentId) {
  if (!documentId) return;

  try {
    const response = await apiFetch(`${API_URL}/documents/${documentId}`, {
      method: 'DELETE',
      headers: {
        ...getAuthHeaders(),
      },
    });

    if (!response.ok) {
      const data = await responseJson(response, 'Unable to delete the document.');
      throw new ApiError(data.detail || 'Unable to delete the document.', response.status);
    }

    return await responseJson(response, 'Unable to delete the document.');
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw new ApiError('Unable to delete the document. Please try again.', 0);
  }
}

// ============================================================
// AUTHENTICATION
// ============================================================

export async function signupUser(email, password, fullName = '') {
  const response = await apiFetch(`${API_URL}/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, full_name: fullName }),
  });

  const data = await responseJson(response, 'Sign up failed.');
  if (!response.ok) {
    throw new ApiError(data.detail || 'Sign up failed', response.status);
  }
  return data;
}

export async function loginUser(email, password) {
  const response = await apiFetch(`${API_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  const data = await responseJson(response, 'Login failed.');
  if (!response.ok) {
    throw new ApiError(data.detail || 'Invalid login credentials', response.status);
  }
  return data;
}

export async function sendOtp(email, purpose = 'login') {
  const response = await apiFetch(`${API_URL}/auth/send-otp`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, purpose }),
  });

  const data = await responseJson(response, 'Failed to send verification code.');
  if (!response.ok) {
    throw new ApiError(data.detail || 'Failed to send verification code', response.status);
  }
  return data;
}

export async function verifyOtp(email, otp, purpose = 'login', password = '', fullName = '') {
  const response = await apiFetch(`${API_URL}/auth/verify-otp`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email,
      otp,
      purpose,
      password: password || undefined,
      full_name: fullName || undefined,
    }),
  });

  const data = await responseJson(response, 'Invalid verification code.');
  if (!response.ok) {
    throw new ApiError(data.detail || 'Invalid verification code', response.status);
  }
  return data;
}

export async function getCurrentUser() {
  const token = localStorage.getItem('docai_token');
  if (!token) return null;

  try {
    const response = await apiFetch(`${API_URL}/auth/me`, {
      headers: { ...getAuthHeaders() },
    });
    if (!response.ok) {
      localStorage.removeItem('docai_token');
      localStorage.removeItem('docai_session_id');
      return null;
    }
    return await response.json();
  } catch {
    return null;
  }
}

export async function logoutUser() {
  try {
    await apiFetch(`${API_URL}/auth/logout`, {
      method: 'POST',
      headers: { ...getAuthHeaders() },
    });
  } catch {
    // Ignore network error on logout
  } finally {
    localStorage.removeItem('docai_token');
    localStorage.removeItem('docai_session_id');
  }
}

export async function refreshToken() {
  try {
    const response = await apiFetch(`${API_URL}/auth/refresh`, {
      method: 'POST',
      headers: { ...getAuthHeaders() },
    });
    if (response.ok) {
      const data = await response.json();
      if (data.token) {
        localStorage.setItem('docai_token', data.token);
      }
      return data;
    }
  } catch {
    // Silently continue
  }
  return null;
}

export async function getPurchaseHistory() {
  const response = await apiFetch(`${API_URL}/auth/history`, {
    headers: { ...getAuthHeaders() },
  });
  const data = await responseJson(response, 'Failed to fetch history.');
  if (!response.ok) {
    throw new ApiError(data.detail || 'Failed to fetch history', response.status);
  }
  return data;
}

// ============================================================
// PAYMENTS & PLANS
// ============================================================

export async function getPlans() {
  const response = await apiFetch(`${API_URL}/payments/plans`);
  return await responseJson(response, 'Failed to load plans.');
}

export async function createOrder(planOrPayload, currency = 'INR') {
  const payload = typeof planOrPayload === 'object'
    ? planOrPayload
    : { plan: planOrPayload, currency };

  const response = await apiFetch(`${API_URL}/payments/create-order`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify(payload),
  });

  const data = await responseJson(response, 'Failed to create payment order.');
  if (!response.ok) {
    throw new ApiError(data.detail || 'Failed to create payment order', response.status);
  }
  return data;
}

export async function verifyPayment(orderId, paymentId, signature = '') {
  const payload = typeof orderId === 'object'
    ? orderId
    : {
        order_id: orderId,
        payment_id: paymentId,
        signature: signature,
      };

  const response = await apiFetch(`${API_URL}/payments/verify-payment`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify(payload),
  });

  const data = await responseJson(response, 'Payment verification failed.');
  if (!response.ok) {
    throw new ApiError(data.detail || 'Payment verification failed', response.status);
  }
  return data;
}

export { ApiError };
