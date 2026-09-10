/**
 * Builds the SVG coordinate grids some questions ship as data:
 * `{ xEnd, yEnd, step, draw }`, where `draw` is raw SVG in graph coordinates.
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
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" class="coordinate-grid no-copy"${described}>
      <style>.graph-content * { vector-effect: non-scaling-stroke; }</style>
      ${gridLines(geometry)}
      <g class="graph-content" transform="translate(${geometry.centerX}, ${geometry.centerY}) scale(${PIXELS_PER_UNIT}, -${PIXELS_PER_UNIT})">
        ${draw}
      </g>
    </svg>`;
}

/**
 * Render whatever a question carries in `image`: a grid descriptor, raw SVG/HTML,
 * or nothing at all.
 * @returns {string} markup, empty when the question has no figure.
 */
export function renderQuestionFigure(image) {
  if (image && typeof image === 'object') return renderCoordinateGrid(image);
  if (typeof image === 'string' && image && image !== 'null') return image;
  return '';
}
