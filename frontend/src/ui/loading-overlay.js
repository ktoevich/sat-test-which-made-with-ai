/** Full-screen loading message and the pre-module countdown. */

import { COUNTDOWN_SECONDS } from '../config.js';
import { byId, hide, setHtml, setText, show } from '../core/dom.js';

const overlay = () => byId('loading-overlay');
const textEl = () => byId('loading-text');
const countdownEl = () => byId('countdown');
const countdownNumber = () => byId('countdown-number');

export function showLoading(message) {
  setHtml(textEl(), `${message}<span class="loading-dots"></span>`);
  show(textEl());
  hide(countdownEl());
  show(overlay());
}

export function hideLoading() {
  hide(overlay());
}

/** Count down on screen, then hide the overlay. Resolves when it reaches zero. */
export function runCountdown(seconds = COUNTDOWN_SECONDS) {
  return new Promise((resolve) => {
    hide(textEl());
    show(countdownEl());

    let remaining = seconds;
    setText(countdownNumber(), remaining);

    const interval = setInterval(() => {
      remaining -= 1;
      if (remaining > 0) {
        setText(countdownNumber(), remaining);
        return;
      }
      clearInterval(interval);
      hideLoading();
      show(textEl());
      hide(countdownEl());
      resolve();
    }, 1000);
  });
}
