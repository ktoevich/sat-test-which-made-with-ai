/**
 * Theme and language that follow the account, not just the browser.
 *
 * On sign-in the settings the account has are applied; a setting the account
 * does not have yet takes what this browser uses, so the first device sets
 * them. While someone is signed in, switching the theme or the language is
 * saved to the account as well as to the browser.
 */

import { saveSettings } from '../../api/auth-api.js';
import { currentLanguage, LANGUAGES, setLanguage } from '../../core/i18n.js';
import { applyTheme, currentTheme, THEMES } from '../../core/theme.js';

export class SettingsSync {
  constructor() {
    this.signedIn = false;
    /** True while applying the account's settings, so they are not sent back. */
    this.applying = false;
    document.addEventListener('themechange', (event) => this.#save({ theme: event.detail.theme }));
    document.addEventListener('languagechange', (event) => this.#save({ language: event.detail.language }));
  }

  /** Apply what the account has and store what it is missing. */
  adopt(settings = {}) {
    this.applying = true;
    try {
      if (THEMES.includes(settings.theme) && settings.theme !== currentTheme()) applyTheme(settings.theme);
      if (LANGUAGES.includes(settings.language) && settings.language !== currentLanguage()) setLanguage(settings.language);
    } finally {
      this.applying = false;
    }
    this.signedIn = true;

    const missing = {};
    if (!settings.theme) missing.theme = currentTheme();
    if (!settings.language) missing.language = currentLanguage();
    if (Object.keys(missing).length) this.#save(missing);
  }

  /** Signed out: changes stay in this browser only. */
  stop() {
    this.signedIn = false;
  }

  #save(changes) {
    if (!this.signedIn || this.applying) return;
    // The browser already switched; an account that cannot be reached catches up next time.
    saveSettings(changes).catch(() => {});
  }
}
