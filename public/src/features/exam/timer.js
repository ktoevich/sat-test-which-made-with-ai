/** Countdown timer shown in the top bar. */

import { byId, setText, setVisible } from '../../core/dom.js';

const formatClock = (totalSeconds) => {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
};

export class ExamTimer {
  /** @param {{ onExpire: () => void }} options */
  constructor({ onExpire }) {
    this.onExpire = onExpire;
    this.intervalId = null;
    this.hidden = false;

    this.elements = {
      container: byId('timer'),
      value: byId('timer-value'),
      icon: byId('timer-icon'),
    };

    this.elements.container.addEventListener('click', () => this.toggleVisibility());
  }

  start(durationSeconds) {
    this.stop();
    let remaining = durationSeconds;
    setText(this.elements.value, formatClock(remaining));

    this.intervalId = setInterval(() => {
      remaining -= 1;
      if (remaining < 0) {
        this.stop();
        this.onExpire();
        return;
      }
      setText(this.elements.value, formatClock(remaining));
    }, 1000);
  }

  stop() {
    if (this.intervalId !== null) clearInterval(this.intervalId);
    this.intervalId = null;
  }

  /** Students can hide the clock, like on the real test. */
  toggleVisibility() {
    this.hidden = !this.hidden;
    setVisible(this.elements.value, !this.hidden);
    setVisible(this.elements.icon, this.hidden);
  }
}
