/** Animates the liquid fill inside a score circle. */

import { scoreFillPercent } from '../../core/scoring.js';
import { setText } from '../../core/dom.js';

/**
 * @param {{ valueEl: HTMLElement, fillEl: HTMLElement }} elements
 * @param {number} score
 */
export function renderScoreBubble({ valueEl, fillEl }, score) {
  setText(valueEl, score);
  // Start from empty so the CSS transition on `top` always plays.
  fillEl.style.top = '100%';
  requestAnimationFrame(() => {
    fillEl.style.top = `${100 - scoreFillPercent(score)}%`;
  });
}
