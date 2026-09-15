/** Endpoints of the exam API. The rest of the app never builds URLs itself. */

import { DEFAULT_SECTION } from '../config.js';
import { apiGet } from './client.js';

/**
 * @typedef {{ test_id: string, section: string, module: number, questions: object[] }} ModulePayload
 */

/**
 * @param {string} section `math` or `reading`
 * @returns {Promise<ModulePayload>}
 */
export function fetchModule1(section = DEFAULT_SECTION) {
  return apiGet('/tests/module-1', { section });
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
