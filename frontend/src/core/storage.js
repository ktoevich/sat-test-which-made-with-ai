/**
 * Browser-side session storage.
 *
 * Accounts and test history live in the backend database now; the only thing
 * kept in the browser is the session token issued at sign-in. It is scoped to
 * this origin and cleared on logout.
 */

import { STORAGE_PREFIX } from '../config.js';

const TOKEN_KEY = `${STORAGE_PREFIX}_session_token`;

export const session = {
  readToken() {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },

  writeToken(token) {
    try {
      localStorage.setItem(TOKEN_KEY, token);
    } catch {
      // A browser with storage disabled still works; the session just ends
      // when the tab closes.
    }
  },

  clear() {
    try {
      localStorage.removeItem(TOKEN_KEY);
    } catch {
      // Nothing to clean up.
    }
  },
};
