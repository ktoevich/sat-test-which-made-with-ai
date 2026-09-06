/** Endpoints of the exam API. The rest of the app never builds URLs itself. */

import { apiGet } from './client.js';

/**
 * @typedef {{ test_id: string, module: number, questions: object[] }} ModulePayload
 */

/** @returns {Promise<ModulePayload>} */
export function fetchModule1() {
  return apiGet('/tests/module-1');
}

/**
 * @param {{ testId: string, target: 'HIGHER' | 'LOWER' }} options
 * @returns {Promise<ModulePayload>}
 */
export function fetchModule2({ testId, target }) {
  return apiGet('/tests/module-2', { test_id: testId, target });
}

export function fetchHealth() {
  return apiGet('/health');
}
