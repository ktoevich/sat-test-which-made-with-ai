/** Endpoints of the exam API. The rest of the app never builds URLs itself. */

import { DEFAULT_SECTION } from '../config.js';
import { apiGet } from './client.js';

/**
 * @typedef {{ test_id: string, section: string, module: number, questions: object[] }} ModulePayload
 */

/**
 * @param {string} section `math` or `reading`
 * @param {{ testId?: string }} [options] a specific test to retake
 * @returns {Promise<ModulePayload>}
 */
export function fetchModule1(section = DEFAULT_SECTION, { testId } = {}) {
  return apiGet('/tests/module-1', { section, test_id: testId || undefined });
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
