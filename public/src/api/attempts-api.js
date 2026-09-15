/** Test history for the signed-in user. */

import { apiGet, apiPost } from './client.js';

/** @returns {Promise<{attempts: object[], summary: {taken: number, best: number|null, average: number|null}}>} */
export function listAttempts() {
  return apiGet('/attempts');
}

/** @returns {Promise<{attempt: object}>} */
export function saveAttempt({ section, score, correct, total, details }) {
  return apiPost('/attempts', { section, score, correct, total, details });
}
