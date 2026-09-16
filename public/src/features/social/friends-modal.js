/** The friends modal: your friends, requests waiting for you, requests you sent, and a search to add more. */

import { ApiError } from '../../api/client.js';
import { searchUsers } from '../../api/community-api.js';
import {
  acceptFriendRequest,
  fetchFriends,
  removeFriendRequest,
  sendFriendRequest,
  unfriend,
} from '../../api/social-api.js';
import { byId, clear, el, setText } from '../../core/dom.js';
import { t } from '../../core/i18n.js';
import { openModal } from '../../ui/modal.js';

const avatarOf = (user) => user?.avatar || '🎓';

export class FriendsModal {
  /** @param {{ onViewUser: (id: number) => void, onMessage: (id: number) => void, onChanged: () => void }} handlers */
  constructor(handlers) {
    this.handlers = handlers;
    this.tab = 'friends';
    this.overview = { friends: [], incoming: [], outgoing: [] };
    this.elements = {
      tabs: byId('friends-tabs'),
      list: byId('friends-list'),
      findPane: byId('friends-pane-find'),
      search: byId('friends-search'),
      countList: byId('friends-count-list'),
      countIncoming: byId('friends-count-incoming'),
    };
    this.elements.tabs.querySelectorAll('[data-tab]').forEach((button) => {
      button.addEventListener('click', () => this.#switchTab(button.dataset.tab));
    });
    let timer = null;
    this.elements.search.addEventListener('input', () => {
      clearTimeout(timer);
      timer = setTimeout(() => this.#renderFind(), 180);
    });
  }

  async open(tab = 'friends') {
    openModal('friends-modal');
    await this.refresh();
    this.#switchTab(tab);
  }

  async refresh() {
    try {
      this.overview = await fetchFriends();
    } catch {
      this.overview = { friends: [], incoming: [], outgoing: [] };
    }
    setText(this.elements.countList, this.overview.friends.length || '');
    setText(this.elements.countIncoming, this.overview.incoming.length || '');
    this.#render();
  }

  #switchTab(tab) {
    this.tab = tab;
    this.elements.tabs.querySelectorAll('[data-tab]').forEach((button) => {
      button.classList.toggle('is-active', button.dataset.tab === tab);
    });
    this.elements.findPane.hidden = tab !== 'find';
    if (tab === 'find') {
      this.elements.search.focus();
      this.#renderFind();
    } else {
      this.#render();
    }
  }

  #person(user, subtitle, actions) {
    const name = el('div', { className: 'person__name', text: user.username });
    name.addEventListener('click', () => this.handlers.onViewUser(user.id));
    return el('li', { className: 'person' }, [
      el('span', { className: 'person__avatar', text: avatarOf(user) }),
      el('div', { className: 'person__who' }, [name, el('div', { className: 'person__sub', text: subtitle })]),
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

  #render() {
    const { list } = this.elements;
    clear(list);
    if (this.tab === 'find') return;
    const entries = this.overview[this.tab] ?? [];
    const empty = { friends: 'friends_empty', incoming: 'friends_incoming_empty', outgoing: 'friends_outgoing_empty' }[this.tab];
    if (!entries.length) {
      list.append(el('li', { className: 'side-empty', text: t(empty) }));
      return;
    }
    entries.forEach((entry) => {
      const subtitle = `${t(`tier_${entry.user.tier}`)} · ${entry.user.rating}`;
      let actions;
      if (this.tab === 'friends') {
        const message = el('button', { type: 'button', className: 'btn-primary btn--small', text: t('profile_message') });
        message.addEventListener('click', () => this.handlers.onMessage(entry.user.id));
        actions = [message, this.#button(t('profile_unfriend'), 'btn-secondary', () => unfriend(entry.user.id))];
      } else if (this.tab === 'incoming') {
        actions = [
          this.#button(t('friends_accept'), 'btn-primary', () => acceptFriendRequest(entry.request_id)),
          this.#button(t('friends_decline'), 'btn-secondary', () => removeFriendRequest(entry.request_id)),
        ];
      } else {
        actions = [this.#button(t('friends_cancel'), 'btn-secondary', () => removeFriendRequest(entry.request_id))];
      }
      list.append(this.#person(entry.user, subtitle, actions));
    });
  }

  async #renderFind() {
    const { list, search } = this.elements;
    clear(list);
    let users = [];
    try {
      ({ users } = await searchUsers(search.value.trim(), 12));
    } catch {
      users = [];
    }
    if (!users.length) {
      list.append(el('li', { className: 'side-empty', text: t('side_search_empty') }));
      return;
    }
    const known = new Map();
    this.overview.friends.forEach((f) => known.set(f.user.id, 'friends'));
    this.overview.incoming.forEach((f) => known.set(f.user.id, 'incoming'));
    this.overview.outgoing.forEach((f) => known.set(f.user.id, 'outgoing'));
    users.forEach((user) => {
      const state = known.get(user.id);
      let action;
      if (state === 'friends') action = el('span', { className: 'person__sub', text: t('profile_friends_since') });
      else if (state === 'outgoing') action = el('span', { className: 'person__sub', text: t('friends_added') });
      else if (state === 'incoming') {
        const request = this.overview.incoming.find((f) => f.user.id === user.id);
        action = this.#button(t('friends_accept'), 'btn-primary', () => acceptFriendRequest(request.request_id));
      } else action = this.#button(t('friends_add'), 'btn-primary', () => sendFriendRequest(user.id));
      list.append(this.#person(user, [user.full_name, user.location].filter(Boolean).join(' · ') || `${user.rating}`, [action]));
    });
  }
}
