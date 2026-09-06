/**
 * Sign-in / sign-up screen.
 *
 * Credentials go to the backend, which stores a one-way password hash and
 * returns a session token. Nothing about the password stays in the browser.
 */

import { login, register } from '../../api/auth-api.js';
import { ApiError } from '../../api/client.js';
import { byId, setText, setVisible } from '../../core/dom.js';
import { session } from '../../core/storage.js';

const MODE = { LOGIN: 'login', REGISTER: 'register' };

const COPY = {
  [MODE.LOGIN]: {
    title: 'Welcome back!',
    subtitle: 'Enter your credentials to log in',
    submit: 'Log In',
  },
  [MODE.REGISTER]: {
    title: 'Create an account',
    subtitle: 'Create a username and password',
    submit: 'Sign Up',
  },
};

const MIN_PASSWORD_LENGTH = 8;

export class AuthScreen {
  /** @param {{ onAuthenticated: (user: object) => void }} options */
  constructor({ onAuthenticated }) {
    this.onAuthenticated = onAuthenticated;
    this.mode = MODE.LOGIN;
    this.busy = false;

    this.elements = {
      form: byId('auth-form'),
      tabs: [byId('auth-tab-login'), byId('auth-tab-register')],
      title: byId('auth-title'),
      subtitle: byId('auth-subtitle'),
      submit: byId('auth-submit'),
      error: byId('auth-error'),
      usernameField: byId('auth-username-field'),
      confirmField: byId('auth-confirm-field'),
      username: byId('auth-username'),
      email: byId('auth-email'),
      password: byId('auth-password'),
      confirm: byId('auth-confirm'),
    };

    this.#bindEvents();
    this.#applyMode();
  }

  #bindEvents() {
    this.elements.tabs.forEach((tab) => {
      tab.addEventListener('click', () => this.#switchMode(tab.dataset.authMode));
    });
    this.elements.form.addEventListener('submit', (event) => {
      event.preventDefault();
      this.#submit();
    });
  }

  /** Return the form to a clean "Log In" state, e.g. after a logout. */
  reset() {
    this.mode = MODE.LOGIN;
    this.#clearInputs();
    this.#applyMode();
  }

  #switchMode(mode) {
    if (!mode || mode === this.mode) return;
    this.mode = mode;
    this.#clearInputs();
    this.#applyMode();
  }

  #applyMode() {
    const copy = COPY[this.mode];
    const isRegister = this.mode === MODE.REGISTER;

    this.elements.tabs.forEach((tab) => {
      tab.classList.toggle('is-active', tab.dataset.authMode === this.mode);
    });
    setText(this.elements.title, copy.title);
    setText(this.elements.subtitle, copy.subtitle);
    setText(this.elements.submit, copy.submit);
    setVisible(this.elements.usernameField, isRegister);
    setVisible(this.elements.confirmField, isRegister);
    this.elements.password.autocomplete = isRegister ? 'new-password' : 'current-password';
    this.#showError('');
  }

  #clearInputs() {
    ['username', 'email', 'password', 'confirm'].forEach((key) => {
      this.elements[key].value = '';
    });
  }

  #showError(message) {
    setText(this.elements.error, message);
  }

  #setBusy(busy) {
    this.busy = busy;
    this.elements.submit.disabled = busy;
    setText(this.elements.submit, busy ? 'Please wait...' : COPY[this.mode].submit);
  }

  #readForm() {
    return {
      email: this.elements.email.value.trim(),
      password: this.elements.password.value,
      username: this.elements.username.value.trim(),
      confirm: this.elements.confirm.value,
    };
  }

  /** Checks worth doing before spending a round trip. */
  #localProblem(form) {
    if (!form.email || !form.password) return 'Please fill in Email and Password.';
    if (this.mode !== MODE.REGISTER) return null;
    if (!form.username) return 'Please enter a username.';
    if (form.password.length < MIN_PASSWORD_LENGTH) {
      return `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`;
    }
    if (form.password !== form.confirm) return 'Passwords do not match.';
    return null;
  }

  async #submit() {
    if (this.busy) return;

    const form = this.#readForm();
    const problem = this.#localProblem(form);
    if (problem) {
      this.#showError(problem);
      return;
    }

    this.#showError('');
    this.#setBusy(true);
    try {
      const result =
        this.mode === MODE.REGISTER
          ? await register({ email: form.email, username: form.username, password: form.password })
          : await login({ email: form.email, password: form.password });

      session.writeToken(result.token);
      this.#clearInputs();
      this.onAuthenticated(result.user);
    } catch (error) {
      this.#showError(
        error instanceof ApiError ? error.message : 'Something went wrong. Please try again.',
      );
    } finally {
      this.#setBusy(false);
    }
  }
}
