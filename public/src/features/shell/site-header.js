/** The header above the lobby: brand, language and theme switches, messages, notifications, the profile chip. */

import { byId, setText, setVisible } from '../../core/dom.js';

export class SiteHeader {
  /**
   * @param {{ onHome: () => void, onProfile: () => void, onMessages: () => void,
   *           onNotifications: () => void, onLogout: () => void }} handlers
   */
  constructor({ onHome, onProfile, onMessages, onNotifications, onLogout }) {
    this.elements = {
      header: byId('site-header'),
      avatar: byId('header-avatar'),
      username: byId('header-username'),
      unread: byId('messages-unread'),
      notifications: byId('notifications-unread'),
    };
    byId('brand-home').addEventListener('click', onHome);
    byId('profile-btn').addEventListener('click', onProfile);
    byId('messages-btn').addEventListener('click', onMessages);
    byId('notifications-btn').addEventListener('click', onNotifications);
    byId('logout-btn').addEventListener('click', onLogout);
  }

  setUser(user) {
    setText(this.elements.avatar, user?.avatar || '🎓');
    setText(this.elements.username, user?.username ?? '');
  }

  setUnread(count) {
    setText(this.elements.unread, count);
    setVisible(this.elements.unread, count > 0);
  }

  setNotifications(count) {
    setText(this.elements.notifications, count);
    setVisible(this.elements.notifications, count > 0);
  }
}
