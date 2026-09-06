/** KaTeX integration: one place that knows which delimiters we support. */

const DELIMITERS = [
  { left: '$$', right: '$$', display: true },
  { left: '$', right: '$', display: false },
  { left: '\\(', right: '\\)', display: false },
  { left: '\\[', right: '\\]', display: true },
];

/**
 * Render every formula found inside `root`.
 * No-op while the CDN script is still loading, which keeps the app usable offline.
 */
export function renderMath(root = document.body) {
  if (typeof window.renderMathInElement !== 'function') return;
  window.renderMathInElement(root, { delimiters: DELIMITERS, throwOnError: false });
}
