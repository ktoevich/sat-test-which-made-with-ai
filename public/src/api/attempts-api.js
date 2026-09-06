/** Test history for the signed-in user. */

import { apiGet, apiPost } from './client.js';

/** @returns {Promise<{attempts: object[], summary: {taken: number, best: number|null, average: number|null}}>} */
export function listAttempts() {
  return apiGet('/attempts');
}

/** @returns {Promise<{attempt: object}>} */
export function saveAttempt({ score, correct, total, details }) {
  return apiPost('/attempts', { score, correct, total, details });
}
