/**
 * A test cannot be reloaded away from.
 *
 * While a module runs, the browser's own leave-page prompt is armed and the
 * reload keys open a warning instead of reloading. Should the page still be
 * reloaded, the attempt was mirrored into sessionStorage after every change,
 * so the next load finishes it: unanswered questions count as omitted, and
 * the result is scored and saved like any other.
 */

import { byId } from '../../core/dom.js';
import { closeModal, openModal } from '../../ui/modal.js';

const STORAGE_KEY = 'sat_active_test';

export const activeTestStore = {
  read() {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  },
  write(snapshot) {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot));
    } catch {
      // Storage full or off: the guard still warns; a reload just loses the test.
    }
  },
  clear() {
    try {
      sessionStorage.removeItem(STORAGE_KEY);
    } catch {
      // Nothing to clear.
    }
  },
};

const isReloadKey = (event) =>
  event.key === 'F5' || ((event.ctrlKey || event.metaKey) && (event.key === 'r' || event.key === 'R'));

/**
 * Arm the guard. `isActive` says whether a module is running; `onFinishNow`
 * ends the test when the student chooses to on the warning.
 */
export function installReloadGuard({ isActive, onFinishNow }) {
  window.addEventListener('keydown', (event) => {
    if (!isActive() || !isReloadKey(event)) return;
    event.preventDefault();
    event.stopPropagation();
    openModal('reload-modal');
  });
  window.addEventListener('beforeunload', (event) => {
    if (!isActive()) return;
    event.preventDefault();
    event.returnValue = '';
  });
  byId('reload-finish-btn').addEventListener('click', () => {
    closeModal('reload-modal');
    onFinishNow();
  });
}
