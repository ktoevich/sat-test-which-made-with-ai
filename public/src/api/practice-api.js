/** A short practice set of one domain. */

import { apiGet } from './client.js';

/** @returns {Promise<{section: string, domain: string|null, questions: object[]}>} */
export function fetchPracticeSet({ section, domain, count = 5 }) {
  return apiGet('/practice', { section, domain, count });
}
