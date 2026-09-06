/** Boots index.html inside jsdom and exposes small helpers for the tests. */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { JSDOM } from 'jsdom';

export const FRONTEND_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');

/**
 * Install a jsdom window as the globals the app expects, then import the app.
 * @param {{ fetchImpl: (url: URL) => object }} options
 */
export async function bootApp({ fetchImpl }) {
  const html = fs.readFileSync(path.join(FRONTEND_ROOT, 'index.html'), 'utf8');
  const dom = new JSDOM(html, { url: 'http://127.0.0.1:5000/', pretendToBeVisual: true });

  global.window = dom.window;
  global.document = dom.window.document;
  global.localStorage = dom.window.localStorage;
  global.HTMLElement = dom.window.HTMLElement;
  global.requestAnimationFrame = (callback) => setTimeout(() => callback(0), 0);

  const requests = [];
  let handler = fetchImpl;
  global.fetch = async (url, options = {}) => {
    const parsed = new URL(url);
    requests.push(`${options.method ?? 'GET'} ${parsed.pathname}${parsed.search}`);
    return handler(parsed, options);
  };

  const { App } = await import(path.join(FRONTEND_ROOT, 'src/app.js'));
  await new App().start();

  return { window: dom.window, requests, setFetch: (fn) => { handler = fn; } };
}

export function domHelpers(window) {
  const byId = (id) => window.document.getElementById(id);
  return {
    byId,
    isVisible: (id) => !byId(id).classList.contains('hidden'),
    text: (id) => byId(id).textContent,
    click: (target) => {
      const node = typeof target === 'string' ? byId(target) : target;
      node.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
    },
    type: (input, value) => {
      input.value = value;
      input.dispatchEvent(new window.Event('input', { bubbles: true }));
    },
    submit: (id) =>
      byId(id).dispatchEvent(new window.Event('submit', { bubbles: true, cancelable: true })),
    all: (selector, root) => [...(root ?? window.document).querySelectorAll(selector)],
  };
}

export const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/** Let queued promise callbacks run without advancing timers. */
export const flush = () => wait(0);

/** The app counts down for 3s before each module starts. */
export const COUNTDOWN_WAIT_MS = 3400;
