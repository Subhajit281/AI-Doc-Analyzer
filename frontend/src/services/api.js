const API_URL =
  import.meta.env.VITE_API_URL ||
  'http://127.0.0.1:8000';

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

// ============================================================
// UPLOAD DOCUMENT
// ============================================================

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append('file', file);

  let response;
  try {
    response = await fetch(`${API_URL}/documents/upload`, {
      method: 'POST',
      headers: {
        ...getAuthHeaders(),
      },
      body: formData,
    });
  } catch (err) {
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
  } catch (err) {
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
    response = await fetch(`${API_URL}/documents/${documentId}/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      body: JSON.stringify({
        query: query.trim(),
        conversation_id: conversationId.trim(),
      }),
    });
  } catch (err) {
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
  } catch (err) {
    throw new ApiError('Unable to parse response. Please try again.', response.status);
  }
}

// ============================================================
// DELETE DOCUMENT
// ============================================================

export async function getUserDocuments() {
  try {
    const response = await fetch(`${API_URL}/documents`, {
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
    const response = await fetch(`${API_URL}/documents/${documentId}`, {
      method: 'DELETE',
      headers: {
        ...getAuthHeaders(),
      },
    });

    if (!response.ok) {
      console.warn(`Failed to delete document ${documentId}: status ${response.status}`);
    }

    return await response.json();
  } catch (err) {
    console.warn(`Error deleting document ${documentId}:`, err);
  }
}

// ============================================================
// AUTHENTICATION
// ============================================================

export async function signupUser(email, password, fullName = '') {
  const response = await fetch(`${API_URL}/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, full_name: fullName }),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new ApiError(data.detail || 'Sign up failed', response.status);
  }
  return data;
}

export async function loginUser(email, password) {
  const response = await fetch(`${API_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new ApiError(data.detail || 'Invalid login credentials', response.status);
  }
  return data;
}

export async function sendOtp(email, purpose = 'login') {
  const response = await fetch(`${API_URL}/auth/send-otp`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, purpose }),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new ApiError(data.detail || 'Failed to send verification code', response.status);
  }
  return data;
}

export async function verifyOtp(email, otp, purpose = 'login', password = '', fullName = '') {
  const response = await fetch(`${API_URL}/auth/verify-otp`, {
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

  const data = await response.json();
  if (!response.ok) {
    throw new ApiError(data.detail || 'Invalid verification code', response.status);
  }
  return data;
}

export async function getCurrentUser() {
  const token = localStorage.getItem('docai_token');
  if (!token) return null;

  try {
    const response = await fetch(`${API_URL}/auth/me`, {
      headers: { ...getAuthHeaders() },
    });
    if (!response.ok) {
      localStorage.removeItem('docai_token');
      return null;
    }
    return await response.json();
  } catch {
    return null;
  }
}

export async function getPurchaseHistory() {
  const response = await fetch(`${API_URL}/auth/history`, {
    headers: { ...getAuthHeaders() },
  });
  const data = await response.json();
  if (!response.ok) {
    throw new ApiError(data.detail || 'Failed to fetch history', response.status);
  }
  return data;
}

// ============================================================
// PAYMENTS & PLANS
// ============================================================

export async function getPlans() {
  const response = await fetch(`${API_URL}/payments/plans`);
  return await response.json();
}

export async function createOrder(plan, currency = 'INR') {
  const response = await fetch(`${API_URL}/payments/create-order`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ plan, currency }),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new ApiError(data.detail || 'Failed to create payment order', response.status);
  }
  return data;
}

export async function verifyPayment(orderId, paymentId, signature = '') {
  const response = await fetch(`${API_URL}/payments/verify`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify({
      order_id: orderId,
      payment_id: paymentId,
      signature: signature,
    }),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new ApiError(data.detail || 'Payment verification failed', response.status);
  }
  return data;
}

export { ApiError };