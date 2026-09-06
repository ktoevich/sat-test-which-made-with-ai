/** Wires the screens together and owns the "who is signed in" state. */

import { ApiError } from './api/client.js';
import { currentUser, logout } from './api/auth-api.js';
import { session } from './core/storage.js';
import { AuthScreen } from './features/auth/auth-screen.js';
import { ExamController } from './features/exam/exam-controller.js';
import { LobbyScreen } from './features/lobby/lobby-screen.js';
import { openAttempt } from './features/results/attempt-modal.js';
import { ResultsScreen } from './features/results/results-screen.js';
import { registerModalDismissers } from './ui/modal.js';
import { Screen, showScreen } from './ui/screens.js';

export class App {
  constructor() {
    /** @type {object | null} */
    this.user = null;

    this.auth = new AuthScreen({ onAuthenticated: (user) => this.#enterLobby(user) });

    this.lobby = new LobbyScreen({
      onStartTest: () => this.#startTest(),
      onLogout: () => this.#logout(),
      onViewAttempt: (attempt) => openAttempt(attempt),
    });

    this.results = new ResultsScreen({ onReturnToLobby: () => this.#enterLobby(this.user) });

    this.exam = new ExamController({
      onFinished: (examSession) => this.results.show(examSession),
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
      const { user } = await currentUser();
      await this.#enterLobby(user);
    } catch {
      // An expired or revoked token is not an error worth showing.
      session.clear();
      showScreen(Screen.AUTH);
    }
  }

  async #enterLobby(user) {
    this.user = user;
    this.results.hide();
    this.lobby.clearNotice();
    showScreen(Screen.LOBBY);

    try {
      await this.lobby.render(user);
    } catch (error) {
      if (error instanceof ApiError && error.isUnauthenticated) this.#signOutLocally();
      else throw error;
    }
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
    this.user = null;
    this.results.hide();
    this.auth.reset();
    showScreen(Screen.AUTH);
  }

  async #startTest() {
    this.lobby.clearNotice();
    showScreen(Screen.EXAM);
    await this.exam.startAttempt();
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
