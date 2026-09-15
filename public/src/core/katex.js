/** KaTeX integration: one place that knows which delimiters we support. */

const DELIMITERS = [
  { left: '$$', right: '$$', display: true },
  { left: '$', right: '$', display: false },
  { left: '\\(', right: '\\)', display: false },
  { left: '\\[', right: '\\]', display: true },
];

/** Elements whose text is prose, not formulas: a passage may well mention $5. */
const IGNORED_CLASSES = ['no-math'];

/**
 * Render every formula found inside `root`.
 * No-op while the CDN script is still loading, which keeps the app usable offline.
 */
export function renderMath(root = document.body) {
  if (typeof window.renderMathInElement !== 'function') return;
  window.renderMathInElement(root, {
    delimiters: DELIMITERS,
    ignoredClasses: IGNORED_CLASSES,
    throwOnError: false,
  });
}
