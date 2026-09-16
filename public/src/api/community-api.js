/** Other students: profile edits, search, public profiles, the leaderboard, the platform's numbers. */

import { apiGet, apiPatch } from './client.js';

/** @returns {Promise<{user: object}>} */
export function updateProfile(fields) {
  return apiPatch('/auth/profile', fields);
}

/** @returns {Promise<{users: object[]}>} */
export function searchUsers(query, limit = 8) {
  return apiGet('/users/search', { q: query, limit });
}

/** @returns {Promise<{user: object, summary: object, history: object[], analytics: object, friends_count: number, relationship: string}>} */
export function fetchPublicProfile(userId) {
  return apiGet(`/users/${userId}`);
}

/** @returns {Promise<{section: string, leaderboard: object[]}>} */
export function fetchLeaderboard(section, limit = 10) {
  return apiGet('/leaderboard', { section, limit });
}

/** @returns {Promise<{students: number, tests_taken: number, by_section: object, countries: object[]}>} */
export function fetchPlatformStats() {
  return apiGet('/stats');
}
