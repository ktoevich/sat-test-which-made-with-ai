/**
 * The messages modal: conversations on the left, the open thread on the
 * right. New messages arrive by polling while the modal is open.
 */

import { ApiError } from '../../api/client.js';
import { fetchPublicProfile } from '../../api/community-api.js';
import { fetchConversations, fetchThread, sendMessage } from '../../api/social-api.js';
import { byId, clear, el, setText } from '../../core/dom.js';
import { t } from '../../core/i18n.js';
import { closeModal, openModal } from '../../ui/modal.js';

const POLL_MS = 8000;
const avatarOf = (user) => user?.avatar || '🎓';

const formatTime = (iso) => {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleString(undefined, { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
};

export class MessagesModal {
  /** @param {{ meId: () => number, onUnread: (count: number) => void, onViewUser: (id: number) => void }} handlers */
  constructor(handlers) {
    this.handlers = handlers;
    this.activeUserId = null;
    this.conversations = [];
    this.timer = null;
    this.elements = {
      contacts: byId('messenger-contacts'),
      peer: byId('messenger-peer'),
      thread: byId('messenger-thread'),
      form: byId('messenger-form'),
      input: byId('messenger-input'),
      send: byId('messenger-send'),
    };
    this.elements.form.addEventListener('submit', (event) => {
      event.preventDefault();
      this.#send();
    });
    byId('messages-modal').querySelector('[data-close-modal]').addEventListener('click', () => this.close());
  }

  /** Open the modal, on a specific student's thread when one is given. */
  async open(userId = null) {
    openModal('messages-modal');
    await this.refresh();
    if (userId) await this.#openThread(userId);
    else if (this.conversations.length) await this.#openThread(this.conversations[0].user.id);
    else this.#renderEmptyThread(t('messages_pick'));
    clearInterval(this.timer);
    this.timer = setInterval(() => this.#poll(), POLL_MS);
  }

  close() {
    clearInterval(this.timer);
    this.timer = null;
    closeModal('messages-modal');
  }

  /** Reload the conversation list and report the unread count. */
  async refresh() {
    try {
      const { conversations, unread } = await fetchConversations();
      this.conversations = conversations;
      this.handlers.onUnread(unread);
    } catch {
      this.conversations = [];
    }
    this.#renderContacts();
  }

  async #poll() {
    await this.refresh();
    if (this.activeUserId) await this.#openThread(this.activeUserId, { silent: true });
  }

  #renderContacts() {
    const { contacts } = this.elements;
    clear(contacts);
    if (!this.conversations.length && !this.activeUserId) {
      contacts.append(el('li', { className: 'messenger__empty', text: t('messages_empty') }));
      return;
    }
    this.conversations.forEach((conversation) => {
      const item = el('li', { className: 'contact' }, [
        el('span', { className: 'contact__avatar', text: avatarOf(conversation.user) }),
        el('span', { className: 'contact__who' }, [
          el('div', { className: 'contact__name', text: conversation.user.username }),
          el('div', { className: 'contact__last', text: `${conversation.last_message.mine ? '↗ ' : ''}${conversation.last_message.body}` }),
        ]),
        conversation.unread ? el('span', { className: 'contact__unread', text: conversation.unread }) : null,
      ]);
      item.classList.toggle('is-active', conversation.user.id === this.activeUserId);
      item.addEventListener('click', () => this.#openThread(conversation.user.id));
      contacts.append(item);
    });
  }

  #renderEmptyThread(message) {
    setText(this.elements.peer, '');
    clear(this.elements.thread);
    this.elements.thread.append(el('div', { className: 'messenger__empty', text: message }));
    this.elements.form.classList.add('hidden');
  }

  async #openThread(userId, { silent = false } = {}) {
    this.activeUserId = Number(userId);
    try {
      const { user, messages } = await fetchThread(userId);
      this.#renderThread(user, messages);
      if (!silent) {
        await this.refresh();
        this.elements.input.focus();
      } else {
        this.#renderContacts();
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        this.#renderEmptyThread(error.message);
      }
    }
  }

  #renderThread(user, messages) {
    const { peer, thread, form } = this.elements;
    clear(peer);
    const name = el('button', { type: 'button', className: 'brand', text: `${avatarOf(user)} ${user.username}` });
    name.addEventListener('click', () => {
      this.close();
      this.handlers.onViewUser(user.id);
    });
    peer.append(name);
    form.classList.remove('hidden');
    clear(thread);
    if (!messages.length) {
      thread.append(el('div', { className: 'messenger__empty', text: t('messages_none_yet') }));
      return;
    }
    const me = this.handlers.meId();
    messages.forEach((message) => {
      thread.append(
        el('div', { className: `bubble${message.sender_id === me ? ' bubble--mine' : ''}` }, [
          el('span', { text: message.body }),
          el('span', { className: 'bubble__time', text: formatTime(message.sent_at) }),
        ]),
      );
    });
    thread.scrollTop = thread.scrollHeight;
  }

  async #send() {
    const { input, send } = this.elements;
    const body = input.value.trim();
    if (!body || !this.activeUserId) return;
    send.disabled = true;
    try {
      await sendMessage(this.activeUserId, body);
      input.value = '';
      await this.#openThread(this.activeUserId);
    } catch (error) {
      this.#renderEmptyThread(error instanceof ApiError ? error.message : t('lobby_notice_failed'));
    } finally {
      send.disabled = false;
    }
  }

  /** Start a conversation with someone not yet in the list. */
  async openWith(userId) {
    try {
      const { user } = await fetchPublicProfile(userId);
      if (!this.conversations.some((c) => c.user.id === user.id)) {
        this.conversations.unshift({ user, last_message: { body: '', mine: true }, unread: 0 });
      }
    } catch {
      // The thread call will say the student does not exist.
    }
    await this.open(userId);
  }
}
