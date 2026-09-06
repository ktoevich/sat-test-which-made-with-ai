/** Open/close helpers plus the shared `data-close-modal` wiring. */

import { hide, qsa, show, byId } from '../core/dom.js';

export const openModal = (id) => show(byId(id));
export const closeModal = (id) => hide(byId(id));

/** Wire every `[data-close-modal="<id>"]` button once, at startup. */
export function registerModalDismissers(root = document) {
  qsa('[data-close-modal]', root).forEach((button) => {
    button.addEventListener('click', () => closeModal(button.dataset.closeModal));
  });
}
