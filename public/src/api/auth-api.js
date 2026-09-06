/** Registration, sign-in and the current session. */

import { apiGet, apiPost } from './client.js';

/** @returns {Promise<{token: string, user: object}>} */
export function register({ email, username, password }) {
  return apiPost('/auth/register', { email, username, password });
}

/** @returns {Promise<{token: string, user: object}>} */
export function login({ email, password }) {
  return apiPost('/auth/login', { email, password });
}

export function logout() {
  return apiPost('/auth/logout');
}

/** @returns {Promise<{user: object}>} */
export function currentUser() {
  return apiGet('/auth/me');
}
