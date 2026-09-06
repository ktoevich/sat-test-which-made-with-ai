/** Entry point: boots the app once the DOM is ready. */

import { App } from './app.js';

const start = () => new App().start();

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', start, { once: true });
} else {
  start();
}
