/** Fetch wrapper: attaches the session token and turns error envelopes into typed errors. */

import { API_BASE_URL } from '../config.js';
import { session } from '../core/storage.js';

export class ApiError extends Error {
  constructor(message, { status, code, cause } = {}) {
    super(message, { cause });
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }

  /** True when the backend has no generated tests yet. */
  get isBankEmpty() {
    return this.code === 'bank_empty';
  }

  /** True when the session is missing or no longer valid. */
  get isUnauthenticated() {
    return this.status === 401 || this.code === 'not_authenticated';
  }
}

async function request(method, path, { params = {}, body } = {}) {
  const url = new URL(`${API_BASE_URL}${path}`, window.location.origin);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) url.searchParams.set(key, value);
  });

  const headers = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';

  const token = session.readToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let response;
  try {
    response = await fetch(url, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (cause) {
    throw new ApiError('Cannot reach the server. Is the backend running?', {
      code: 'network_error',
      cause,
    });
  }

  // 204 and other empty replies have no JSON body.
  const payload = response.status === 204 ? null : await response.json().catch(() => null);

  if (!response.ok) {
    const error = payload?.error ?? {};
    throw new ApiError(error.message ?? `Request failed with status ${response.status}`, {
      status: response.status,
      code: error.code ?? 'unknown_error',
    });
  }

  return payload;
}

export const apiGet = (path, params) => request('GET', path, { params });
export const apiPost = (path, body) => request('POST', path, { body });
