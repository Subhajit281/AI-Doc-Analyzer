const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

/**
 * Upload a document for analysis.
 * @param {File} file
 * @returns {Promise<{document_id: string, filename: string, status: string, page_count: number, section_count: number, chunk_count: number}>}
 */
export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append('file', file);

  let response;
  try {
    response = await fetch(`${API_URL}/documents/upload`, {
      method: 'POST',
      body: formData,
    });
  } catch (err) {
    throw new ApiError('Unable to upload the document. Please try again.', 0);
  }

  if (!response.ok) {
    throw new ApiError('Unable to upload the document. Please try again.', response.status);
  }

  try {
    return await response.json();
  } catch (err) {
    throw new ApiError('Unable to upload the document. Please try again.', response.status);
  }
}

/**
 * Ask a question about an uploaded document.
 * @param {string} documentId
 * @param {string} query
 * @returns {Promise<{document_id: string, filename: string, answer: string}>}
 */
export async function askQuestion(documentId, query) {
  let response;

  try {
    response = await fetch(
      `${API_URL}/documents/${documentId}/query`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query }),
      }
    );
  } catch (err) {
    throw new ApiError(
      'Unable to get a response. Please try again.',
      0
    );
  }

  if (!response.ok) {
    let message = 'Unable to get a response. Please try again.';

    try {
      const errorData = await response.json();

      if (typeof errorData.detail === 'string') {
        message = errorData.detail;
      }
    } catch {
      // Keep the default error message
    }

    throw new ApiError(
      message,
      response.status
    );
  }

  try {
    const data = await response.json();

    let answer = data.answer;

    // -----------------------------------------
    // Normalize answer into a plain string
    // -----------------------------------------

    if (typeof answer === 'string') {
      // Already correct
    }

    else if (Array.isArray(answer)) {
      answer = answer
        .map((item) => {
          if (typeof item === 'string') {
            return item;
          }

          if (
            item &&
            typeof item.text === 'string'
          ) {
            return item.text;
          }

          return '';
        })
        .filter(Boolean)
        .join('\n\n');
    }

    else if (
      answer &&
      typeof answer.text === 'string'
    ) {
      answer = answer.text;
    }

    else {
      answer = String(answer ?? '');
    }

    return {
      ...data,
      answer,
    };

  } catch (err) {
    throw new ApiError(
      'Unable to get a response. Please try again.',
      response.status
    );
  }
}

export { ApiError };