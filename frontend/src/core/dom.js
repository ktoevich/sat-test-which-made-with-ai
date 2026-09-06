/** Thin helpers over the DOM API, so feature code stays readable. */

export const byId = (id) => document.getElementById(id);

export const qs = (selector, root = document) => root.querySelector(selector);

export const qsa = (selector, root = document) => [...root.querySelectorAll(selector)];

export const show = (element) => element?.classList.remove('hidden');

export const hide = (element) => element?.classList.add('hidden');

/** Show when `visible` is true, hide otherwise. */
export const setVisible = (element, visible) => element?.classList.toggle('hidden', !visible);

export const setText = (element, value) => {
  if (element) element.textContent = value;
};

export const setHtml = (element, value) => {
  if (element) element.innerHTML = value;
};

export const clear = (element) => {
  if (element) element.replaceChildren();
};

/**
 * Create an element in one call.
 * `options.text` sets textContent, `options.html` sets innerHTML,
 * everything else is applied as an attribute.
 */
export function el(tag, { className, text, html, dataset, ...attrs } = {}, children = []) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  if (html !== undefined) node.innerHTML = html;
  Object.entries(dataset ?? {}).forEach(([key, value]) => {
    node.dataset[key] = value;
  });
  Object.entries(attrs).forEach(([key, value]) => {
    if (value === undefined || value === false || value === null) return;
    node.setAttribute(key, value === true ? '' : value);
  });
  children.filter(Boolean).forEach((child) => node.append(child));
  return node;
}

/** Escape a string before it goes into an innerHTML template. */
export function escapeHtml(value) {
  return String(value ?? '').replace(
    /[&<>"']/g,
    (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char],
  );
}

export const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
