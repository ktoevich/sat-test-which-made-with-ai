/** Registration, sign-in and the current session. */

import { apiGet, apiPatch, apiPost } from './client.js';

/** @returns {Promise<{token: string, user: object, settings: object}>} */
export function register({ email, username, password }) {
  return apiPost('/auth/register', { email, username, password });
}

/** @returns {Promise<{token: string, user: object, settings: object}>} */
export function login({ email, password }) {
  return apiPost('/auth/login', { email, password });
}

export function logout() {
  return apiPost('/auth/logout');
}

/** @returns {Promise<{user: object, settings: object}>} */
export function currentUser() {
  return apiGet('/auth/me');
}

/** Change some of the settings kept with the account (theme, language). */
export function saveSettings(changes) {
  return apiPatch('/auth/settings', changes);
}
