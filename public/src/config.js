/**
 * Runtime configuration.
 *
 * The API lives at `/api` on the same origin as the page — true both when Flask
 * serves the frontend locally and when a CDN serves it next to the deployed
 * function. Override it with the meta tag in index.html when the two are hosted
 * separately, e.g. a static dev server on another port:
 *
 *   <meta name="sat:api-base" content="http://127.0.0.1:5000/api">
 */

const DEFAULT_API_BASE = '/api';

function resolveApiBaseUrl() {
  const configured = document.querySelector('meta[name="sat:api-base"]')?.content.trim();
  return configured ? configured.replace(/\/$/, '') : DEFAULT_API_BASE;
}

export const API_BASE_URL = resolveApiBaseUrl();

/** Time allowed per module, matching the digital SAT math section. */
export const MODULE_DURATION_SECONDS = 35 * 60;

/** Seconds counted down on screen before a module starts. */
export const COUNTDOWN_SECONDS = 3;

/**
 * Correct answers in module 1 that unlock the harder module 2: 15 of the 22
 * questions. Kept as a fraction so a module of another size scales the same way.
 */
export const ADAPTIVE_PASS_MARK = { correct: 15, outOf: 22 };

/** Scaled-score bounds used to convert the raw score. */
export const SCORE_MIN = 200;
export const SCORE_MAX = 800;

/** Prefix for every key this app writes to localStorage. */
export const STORAGE_PREFIX = 'sat';
