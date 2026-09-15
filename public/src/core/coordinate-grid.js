/**
 * Renders a question's figure.
 *
 * Some questions ship a coordinate grid as data — `{ xEnd, yEnd, step, draw }`,
 * where `draw` is raw SVG in graph coordinates — and the grid is built here.
 * Others carry ready-made SVG: College Board's own figures, sized in points,
 * or the diagrams `app.bank.figures` draws, sized by a viewBox alone. Every
 * figure leaves with a pixel width and height and a viewBox, so the stylesheet
 * can scale it down to fit the screen without breaking its proportions.
 */

const PIXELS_PER_UNIT = 20;
const AXIS_COLOR = '#0f172a';
const GRID_COLOR = '#e2e8f0';
const LABEL_COLOR = '#64748b';

function gridLines({ xEnd, yEnd, step, width, height, centerX, centerY }) {
  const parts = [];

  for (let x = -xEnd; x <= xEnd; x += step) {
    const px = centerX + x * PIXELS_PER_UNIT;
    parts.push(`<line x1="${px}" y1="0" x2="${px}" y2="${height}" stroke="${GRID_COLOR}" stroke-width="1"/>`);
    if (x !== 0) {
      parts.push(
        `<text x="${px}" y="${centerY + 15}" font-size="10" fill="${LABEL_COLOR}" text-anchor="middle">${x}</text>`,
      );
    }
  }

  for (let y = -yEnd; y <= yEnd; y += step) {
    const py = centerY - y * PIXELS_PER_UNIT;
    parts.push(`<line x1="0" y1="${py}" x2="${width}" y2="${py}" stroke="${GRID_COLOR}" stroke-width="1"/>`);
    if (y !== 0) {
      parts.push(
        `<text x="${centerX - 8}" y="${py + 4}" font-size="10" fill="${LABEL_COLOR}" text-anchor="end">${y}</text>`,
      );
    }
  }

  parts.push(`<line x1="0" y1="${centerY}" x2="${width}" y2="${centerY}" stroke="${AXIS_COLOR}" stroke-width="2"/>`);
  parts.push(`<line x1="${centerX}" y1="0" x2="${centerX}" y2="${height}" stroke="${AXIS_COLOR}" stroke-width="2"/>`);
  parts.push(`<text x="${width - 10}" y="${centerY - 10}" font-size="12" font-style="italic" fill="${AXIS_COLOR}">x</text>`);
  parts.push(`<text x="${centerX + 10}" y="15" font-size="12" font-style="italic" fill="${AXIS_COLOR}">y</text>`);

  return parts.join('');
}

/** Escape a value for use inside a double-quoted SVG attribute. */
function attribute(value) {
  return String(value).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
}

/** @returns {string} SVG markup for the described grid. */
export function renderCoordinateGrid({ xEnd, yEnd, step, draw = '', alt = '' }) {
  const width = xEnd * 2 * PIXELS_PER_UNIT;
  const height = yEnd * 2 * PIXELS_PER_UNIT;
  const geometry = { xEnd, yEnd, step, width, height, centerX: width / 2, centerY: height / 2 };
  // Without a description a screen reader announces nothing but "graphic".
  const described = alt ? ` role="img" aria-label="${attribute(alt)}"` : '';

  return `
    <svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" class="coordinate-grid no-copy"${described}>
      <style>.graph-content * { vector-effect: non-scaling-stroke; }</style>
      ${gridLines(geometry)}
      <g class="graph-content" transform="translate(${geometry.centerX}, ${geometry.centerY}) scale(${PIXELS_PER_UNIT}, -${PIXELS_PER_UNIT})">
        ${draw}
      </g>
    </svg>`;
}

/** CSS pixels per unit of an SVG length; a bare number is already pixels. */
const PIXELS_PER = { '': 1, px: 1, pt: 96 / 72, pc: 16, in: 96, cm: 96 / 2.54, mm: 96 / 25.4 };

/** @returns {number|null} an SVG length in pixels, or null when it is not absolute. */
function pixels(length) {
  const match = /^\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?)\s*([a-z%]*)\s*$/i.exec(length ?? '');
  if (!match) return null;
  const scale = PIXELS_PER[match[2].toLowerCase()];
  const value = Number(match[1]) * (scale ?? NaN);
  return Number.isFinite(value) && value > 0 ? value : null;
}

/** @returns {{ width: number, height: number }|null} the size a viewBox spans. */
function viewBoxSize(viewBox) {
  const parts = (viewBox ?? '').trim().split(/[\s,]+/).map(Number);
  if (parts.length !== 4 || parts.some((part) => !Number.isFinite(part))) return null;
  const [, , width, height] = parts;
  return width > 0 && height > 0 ? { width, height } : null;
}

const ROOT_TAG = /<svg\b[^>]*>/i;
const SIZE_ATTRIBUTE = /\s(width|height)\s*=\s*"[^"]*"/gi;

function attributeOf(tag, name) {
  const match = new RegExp(`\\s${name}\\s*=\\s*"([^"]*)"`, 'i').exec(tag);
  return match ? match[1] : null;
}

/** Round a pixel size for an attribute; sub-pixel precision is noise here. */
const px = (value) => String(Math.round(value * 100) / 100);

/**
 * Give the root `<svg>` of `markup` a pixel `width`/`height` and a `viewBox`.
 *
 * With both, the browser knows the figure's natural size and proportions, and
 * `max-width`/`max-height` in the stylesheet shrink it like an image. Point
 * sizes (College Board's) become pixels; a viewBox-only figure is measured by
 * its viewBox; a figure with pixel sizes but no viewBox gets one so it can
 * scale at all. Only the root tag is touched — `stroke-width` and nested
 * elements are left alone.
 * @param {string} markup
 * @returns {string}
 */
export function normaliseFigure(markup) {
  const root = ROOT_TAG.exec(markup);
  if (!root) return markup;
  const tag = root[0];

  const viewBox = viewBoxSize(attributeOf(tag, 'viewBox'));
  let width = pixels(attributeOf(tag, 'width'));
  let height = pixels(attributeOf(tag, 'height'));

  if (!(width && height)) {
    if (!viewBox) return markup;
    ({ width, height } = viewBox);
  }

  let attributes = ` width="${px(width)}" height="${px(height)}"`;
  if (!viewBox) attributes += ` viewBox="0 0 ${px(width)} ${px(height)}"`;

  const sized = tag.replace(SIZE_ATTRIBUTE, '').replace(/(\/?>)$/, `${attributes}$1`);
  return markup.slice(0, root.index) + sized + markup.slice(root.index + tag.length);
}

/**
 * Render whatever a question carries in `image`: a grid descriptor, raw SVG/HTML,
 * or nothing at all.
 * @returns {string} markup, empty when the question has no figure.
 */
export function renderQuestionFigure(image) {
  if (image && typeof image === 'object') return renderCoordinateGrid(image);
  if (typeof image === 'string' && image && image !== 'null') return normaliseFigure(image);
  return '';
}
