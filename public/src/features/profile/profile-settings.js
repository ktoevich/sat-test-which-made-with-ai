/** The profile settings modal: avatar, handle, name and location. */

import { ApiError } from '../../api/client.js';
import { updateProfile } from '../../api/community-api.js';
import { byId, clear, el, setText } from '../../core/dom.js';
import { t } from '../../core/i18n.js';
import { closeModal, openModal } from '../../ui/modal.js';

export const AVATARS = ['🎓', '🦉', '🚀', '⚡', '🦁', '🎯', '🧠', '👑', '🐺', '🦊', '💎', '🏆', '🌟', '📚', '🧮', '✏️'];

export class ProfileSettings {
  /** @param {{ onSaved: (user: object) => void }} handlers */
  constructor({ onSaved }) {
    this.onSaved = onSaved;
    this.selectedAvatar = '';
    this.elements = {
      form: byId('settings-form'),
      grid: byId('avatar-grid'),
      username: byId('settings-username'),
      fullName: byId('settings-fullname'),
      location: byId('settings-location'),
      feedback: byId('settings-feedback'),
      save: byId('settings-save'),
    };
    this.#buildAvatars();
    this.elements.form.addEventListener('submit', (event) => {
      event.preventDefault();
      this.#save();
    });
  }

  #buildAvatars() {
    clear(this.elements.grid);
    AVATARS.forEach((avatar) => {
      const button = el('button', { type: 'button', className: 'avatar-option', text: avatar, 'aria-label': avatar });
      button.addEventListener('click', () => this.#select(avatar));
      this.elements.grid.append(button);
    });
  }

  #select(avatar) {
    this.selectedAvatar = avatar;
    this.elements.grid.querySelectorAll('.avatar-option').forEach((button) => {
      button.classList.toggle('is-selected', button.textContent === avatar);
    });
  }

  open(user) {
    this.#select(user.avatar || AVATARS[0]);
    this.elements.username.value = user.username ?? '';
    this.elements.fullName.value = user.full_name ?? '';
    this.elements.location.value = user.location ?? '';
    this.#feedback('');
    openModal('settings-modal');
    this.elements.username.focus();
  }

  #feedback(message, { error = false } = {}) {
    setText(this.elements.feedback, message);
    this.elements.feedback.classList.toggle('is-error', error);
  }

  async #save() {
    const { username, fullName, location, save } = this.elements;
    save.disabled = true;
    try {
      const { user } = await updateProfile({
        username: username.value,
        avatar: this.selectedAvatar,
        full_name: fullName.value,
        location: location.value,
      });
      this.#feedback(t('settings_saved'));
      this.onSaved(user);
      setTimeout(() => closeModal('settings-modal'), 400);
    } catch (error) {
      this.#feedback(error instanceof ApiError ? error.message : t('lobby_notice_failed'), { error: true });
    } finally {
      save.disabled = false;
    }
  }
}
