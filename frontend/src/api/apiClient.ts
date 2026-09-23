/**
 * frontend/src/api/apiClient.ts
 *
 * Base HTTP client for SIH26143 Read-Only Data Bridge.
 * Handles structured API errors with status and error codes.
 */

export class ApiError extends Error {
  statusCode: number;
  errorCode: string;

  constructor(statusCode: number, errorCode: string, message: string) {
    super(message);
    this.name = 'ApiError';
    this.statusCode = statusCode;
    this.errorCode = errorCode;
  }
}

// In local dev with Vite proxy, base URL is empty string (relative /api)
// Can be overridden by VITE_API_BASE_URL if needed
const BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export async function apiFetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    headers: {
      'Accept': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    let errorCode = 'UNKNOWN_ERROR';
    let errorMessage = `Request failed with status ${response.status}`;

    try {
      const errorBody = await response.json();
      if (errorBody.detail) {
        if (typeof errorBody.detail === 'object') {
          errorCode = errorBody.detail.error || errorCode;
          errorMessage = errorBody.detail.message || errorMessage;
        } else if (typeof errorBody.detail === 'string') {
          errorMessage = errorBody.detail;
        }
      } else if (errorBody.error) {
        errorCode = errorBody.error;
        errorMessage = errorBody.message || errorMessage;
      }
    } catch {
      // Non-JSON error body fallback
    }

    throw new ApiError(response.status, errorCode, errorMessage);
  }

  return response.json() as Promise<T>;
}
