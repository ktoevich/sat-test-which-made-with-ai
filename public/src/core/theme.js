/**
 * Light or dark, remembered per browser.
 *
 * The choice lives in `data-theme` on `<html>`; tokens.css defines the dark
 * palette under that attribute. index.html applies the stored theme in an
 * inline script before the first paint, so a dark page never flashes white.
 */

const STORAGE_KEY = 'sat_theme';
export const THEMES = ['light', 'dark'];

export function currentTheme() {
  return document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light';
}

export function applyTheme(theme) {
  const chosen = THEMES.includes(theme) ? theme : 'light';
  document.documentElement.dataset.theme = chosen;
  try {
    localStorage.setItem(STORAGE_KEY, chosen);
  } catch {
    // Storage may be off; the page still switches.
  }
  document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
    button.setAttribute('aria-pressed', String(chosen === 'dark'));
    button.classList.toggle('is-dark', chosen === 'dark');
  });
  document.dispatchEvent(new CustomEvent('themechange', { detail: { theme: chosen } }));
}

export function toggleTheme() {
  applyTheme(currentTheme() === 'dark' ? 'light' : 'dark');
}

/** Apply the remembered theme (the inline script may have done it already) and wire the toggles. */
export function initTheme() {
  let stored = null;
  try {
    stored = localStorage.getItem(STORAGE_KEY);
  } catch {
    stored = null;
  }
  applyTheme(stored ?? currentTheme());
  document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
    button.addEventListener('click', toggleTheme);
  });
}
