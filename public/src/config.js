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

/**
 * The Desmos graphing calculator the exam offers, loaded from Desmos's API.
 * The built-in key is the demo key Desmos publishes for development; a
 * deployment should request its own free key at https://www.desmos.com/api
 * and put it in the `sat:desmos-api-key` meta tag in index.html.
 */
const DESMOS_DEMO_API_KEY = 'dcb31709b452b1cf9dc26972add0dda6';

function resolveDesmosApiKey() {
  const configured = document.querySelector('meta[name="sat:desmos-api-key"]')?.content.trim();
  return configured || DESMOS_DEMO_API_KEY;
}

export const DESMOS_SCRIPT_URL =
  `https://www.desmos.com/api/v1.10/calculator.js?apiKey=${encodeURIComponent(resolveDesmosApiKey())}`;

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
