/**
 * The notifications modal: friend requests that came in and requests that
 * were accepted. A request still waiting can be answered right here; opening
 * the modal marks everything in it as read.
 */

import { ApiError } from '../../api/client.js';
import {
  acceptFriendRequest,
  fetchNotifications,
  markNotificationsRead,
  removeFriendRequest,
} from '../../api/social-api.js';
import { byId, clear, el, setText } from '../../core/dom.js';
import { t } from '../../core/i18n.js';
import { closeModal, openModal } from '../../ui/modal.js';

const avatarOf = (user) => user?.avatar || '🎓';

const formatTime = (iso) => {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleString(undefined, { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
};

const TEXT_KEY = {
  friend_request: 'notif_friend_request',
  friend_accepted: 'notif_friend_accepted',
};

export class NotificationsModal {
  /** @param {{ onUnread: (count: number) => void, onViewUser: (id: number) => void, onChanged: () => void }} handlers */
  constructor(handlers) {
    this.handlers = handlers;
    this.items = [];
    this.elements = { modal: byId('notifications-modal'), list: byId('notifications-list') };
    document.addEventListener('languagechange', () => {
      if (!this.elements.modal.classList.contains('hidden')) this.#render();
    });
  }

  async open() {
    openModal('notifications-modal');
    await this.refresh();
    if (this.items.some((item) => !item.read)) {
      try {
        this.handlers.onUnread((await markNotificationsRead()).unread);
      } catch {
        // They stay unread and are marked the next time.
      }
    }
  }

  /** Reload the list and report the unread count. */
  async refresh() {
    try {
      const { notifications, unread } = await fetchNotifications();
      this.items = notifications;
      this.handlers.onUnread(unread);
    } catch {
      this.items = [];
    }
    this.#render();
  }

  #render() {
    const { list } = this.elements;
    clear(list);
    if (!this.items.length) {
      list.append(el('li', { className: 'side-empty', text: t('notif_empty') }));
      return;
    }
    this.items.forEach((item) => list.append(this.#item(item)));
  }

  #item(item) {
    const name = el('span', { className: 'person__name', text: item.user.username });
    name.addEventListener('click', () => {
      closeModal('notifications-modal');
      this.handlers.onViewUser(item.user.id);
    });
    const [before, after = ''] = t(TEXT_KEY[item.kind] ?? 'notif_other').split('{name}');
    const actions = item.pending
      ? [
          this.#button(t('friends_accept'), 'btn-primary', () => acceptFriendRequest(item.ref_id)),
          this.#button(t('friends_decline'), 'btn-secondary', () => removeFriendRequest(item.ref_id)),
        ]
      : [];
    return el('li', { className: `person notification${item.read ? '' : ' is-unread'}` }, [
      el('span', { className: 'person__avatar', text: avatarOf(item.user) }),
      el('div', { className: 'person__who' }, [
        el('div', { className: 'notification__text' }, [before, name, after]),
        el('div', { className: 'person__sub', text: formatTime(item.created_at) }),
      ]),
      el('div', { className: 'person__actions' }, actions),
    ]);
  }

  #button(label, className, action) {
    const button = el('button', { type: 'button', className: `${className} btn--small`, text: label });
    button.addEventListener('click', async () => {
      button.disabled = true;
      try {
        await action();
        await this.refresh();
        this.handlers.onChanged?.();
      } catch (error) {
        button.disabled = false;
        setText(button, error instanceof ApiError ? error.message : t('lobby_notice_failed'));
      }
    });
    return button;
  }
}
