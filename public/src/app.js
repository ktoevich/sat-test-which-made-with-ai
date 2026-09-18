/** Wires the screens together and owns the "who is signed in" state. */

import { ApiError } from './api/client.js';
import { currentUser, logout } from './api/auth-api.js';
import { fetchConversations, fetchNotifications } from './api/social-api.js';
import { initLanguage } from './core/i18n.js';
import { session } from './core/storage.js';
import { initTheme } from './core/theme.js';
import { AuthScreen } from './features/auth/auth-screen.js';
import { ExamController } from './features/exam/exam-controller.js';
import { activeTestStore } from './features/exam/reload-guard.js';
import { LobbyScreen } from './features/lobby/lobby-screen.js';
import { PracticeModal } from './features/practice/practice-modal.js';
import { ProfileSettings } from './features/profile/profile-settings.js';
import { SettingsSync } from './features/profile/settings-sync.js';
import { openAttempt } from './features/results/attempt-modal.js';
import { ResultsScreen } from './features/results/results-screen.js';
import { SiteHeader } from './features/shell/site-header.js';
import { FriendsModal } from './features/social/friends-modal.js';
import { MessagesModal } from './features/social/messages-modal.js';
import { NotificationsModal } from './features/social/notifications-modal.js';
import { registerModalDismissers } from './ui/modal.js';
import { Screen, showScreen } from './ui/screens.js';

export class App {
  constructor() {
    /** @type {object | null} */
    this.user = null;

    initTheme();
    initLanguage();
    this.settingsSync = new SettingsSync();

    this.auth = new AuthScreen({
      onAuthenticated: (user, settings) => {
        this.settingsSync.adopt(settings);
        this.#enterLobby(user);
      },
    });

    this.header = new SiteHeader({
      onHome: () => this.lobby.exitObserver(),
      onProfile: () => this.lobby.exitObserver(),
      onMessages: () => this.messages.open(),
      onNotifications: () => this.notifications.open(),
      onLogout: () => this.#logout(),
    });

    this.settings = new ProfileSettings({
      onSaved: (user) => {
        this.user = user;
        this.header.setUser(user);
        this.lobby.refresh();
      },
    });
    this.practice = new PracticeModal();
    this.messages = new MessagesModal({
      meId: () => this.user?.id,
      onUnread: (count) => this.header.setUnread(count),
      onViewUser: (id) => this.lobby.viewUser(id),
    });
    this.notifications = new NotificationsModal({
      onUnread: (count) => this.header.setNotifications(count),
      onViewUser: (id) => this.lobby.viewUser(id),
      onChanged: () => this.lobby.refresh(),
    });
    this.friends = new FriendsModal({
      onViewUser: (id) => {
        document.getElementById('friends-modal').classList.add('hidden');
        this.lobby.viewUser(id);
      },
      onMessage: (id) => {
        document.getElementById('friends-modal').classList.add('hidden');
        this.messages.openWith(id);
      },
      onChanged: () => {
        this.lobby.refresh();
        this.#refreshUnread();
      },
    });

    this.lobby = new LobbyScreen({
      onStartTest: (section, testId) => this.#startTest(section, testId),
      onLogout: () => this.#logout(),
      onViewAttempt: (attempt, owner) => openAttempt(attempt, { owner }),
      onPractice: (section, domain) => this.practice.open(section, domain),
      onOpenFriends: () => this.friends.open(),
      onOpenMessages: (userId) => (userId ? this.messages.openWith(userId) : this.messages.open()),
      onOpenSettings: () => this.settings.open(this.user),
    });

    this.results = new ResultsScreen({
      onReturnToLobby: () => this.#enterLobby(this.user),
      onSaved: (attempt) => {
        if (attempt?.rating_after != null && this.user) {
          this.user = { ...this.user, rating: attempt.rating_after, max_rating: Math.max(this.user.max_rating ?? 0, attempt.rating_after) };
        }
      },
    });

    this.exam = new ExamController({
      onFinished: (examSession, options) => this.results.show(examSession, options),
      onUnavailable: (message) => this.#returnToLobbyWithNotice(message),
    });

    registerModalDismissers();
  }

  /** Resume a saved session if the token is still valid, otherwise ask to sign in. */
  async start() {
    if (!session.readToken()) {
      showScreen(Screen.AUTH);
      return;
    }

    try {
      const { user, settings } = await currentUser();
      this.settingsSync.adopt(settings);
      this.user = user;
      this.header.setUser(user);
      // A test that was running when the page reloaded is finished as it stands.
      const interrupted = activeTestStore.read();
      if (interrupted && (await this.exam.resumeTerminated(interrupted))) {
        showScreen(Screen.EXAM);
        return;
      }
      await this.#enterLobby(user);
    } catch {
      // An expired or revoked token is not an error worth showing.
      session.clear();
      showScreen(Screen.AUTH);
    }
  }

  async #enterLobby(user) {
    this.user = user;
    this.header.setUser(user);
    this.results.hide();
    this.lobby.clearNotice();
    showScreen(Screen.LOBBY);
    this.#refreshUnread();

    try {
      await this.lobby.render(user);
    } catch (error) {
      if (error instanceof ApiError && error.isUnauthenticated) this.#signOutLocally();
      else throw error;
    }
  }

  async #refreshUnread() {
    const [conversations, notifications] = await Promise.allSettled([fetchConversations(), fetchNotifications()]);
    this.header.setUnread(conversations.status === 'fulfilled' ? conversations.value.unread : 0);
    this.header.setNotifications(notifications.status === 'fulfilled' ? notifications.value.unread : 0);
  }

  async #logout() {
    try {
      await logout();
    } catch {
      // The local session goes away regardless of what the server says.
    }
    this.#signOutLocally();
  }

  #signOutLocally() {
    session.clear();
    this.settingsSync.stop();
    this.user = null;
    this.results.hide();
    this.auth.reset();
    showScreen(Screen.AUTH);
  }

  async #startTest(section, testId) {
    this.lobby.clearNotice();
    showScreen(Screen.EXAM);
    await this.exam.startAttempt(section, { testId });
  }

  #returnToLobbyWithNotice(message) {
    if (!this.user) {
      showScreen(Screen.AUTH);
      return;
    }
    showScreen(Screen.LOBBY);
    this.lobby.render(this.user).catch(() => this.#signOutLocally());
    this.lobby.showNotice(message);
  }
}
