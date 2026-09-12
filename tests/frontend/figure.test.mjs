/**
 * Every figure a question can carry leaves the renderer with a pixel width and
 * height and a viewBox, which is what lets the stylesheet scale it to fit the
 * screen without distorting it.
 */

import assert from 'node:assert/strict';
import test from 'node:test';

import {
  normaliseFigure,
  renderCoordinateGrid,
  renderQuestionFigure,
} from '../../public/src/core/coordinate-grid.js';

const rootTag = (markup) => /<svg\b[^>]*>/i.exec(markup)[0];
const attribute = (markup, name) =>
  new RegExp(`\\s${name}="([^"]*)"`).exec(rootTag(markup))?.[1] ?? null;

test('a College Board figure sized in points is measured in pixels', () => {
  const figure =
    '<svg height="275.22pt" version="1.1" viewBox="0 0 287.764248 275.22" width="287.764248pt" '
    + 'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Graph of a line">'
    + '<path stroke-width="1.5pt" d="M0 0"/></svg>';

  const out = normaliseFigure(figure);

  assert.equal(attribute(out, 'width'), '383.69');
  assert.equal(attribute(out, 'height'), '366.96');
  assert.equal(attribute(out, 'viewBox'), '0 0 287.764248 275.22');
  assert.equal(attribute(out, 'aria-label'), 'Graph of a line');
  assert.ok(out.includes('stroke-width="1.5pt"'), 'only the root tag is resized');
  assert.ok(out.endsWith('<path stroke-width="1.5pt" d="M0 0"/></svg>'));
});

test('a diagram sized by its viewBox alone gets that size in pixels', () => {
  const figure =
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 336 232" class="question-diagram no-copy" '
    + 'role="img" aria-label="Bar chart"><rect width="10" height="20"/></svg>';

  const out = normaliseFigure(figure);

  assert.equal(attribute(out, 'width'), '336');
  assert.equal(attribute(out, 'height'), '232');
  assert.equal(attribute(out, 'viewBox'), '0 0 336 232');
  assert.ok(out.includes('<rect width="10" height="20"/>'), 'nested sizes are untouched');
});

test('a figure with pixel sizes but no viewBox gets one, so it can scale', () => {
  const out = normaliseFigure('<svg width="400" height="120"><line x1="0" y1="0" x2="400" y2="0"/></svg>');

  assert.equal(attribute(out, 'width'), '400');
  assert.equal(attribute(out, 'height'), '120');
  assert.equal(attribute(out, 'viewBox'), '0 0 400 120');
});

test('a figure that cannot be measured is passed through unchanged', () => {
  const unsized = '<svg xmlns="http://www.w3.org/2000/svg"><circle r="1"/></svg>';
  assert.equal(normaliseFigure(unsized), unsized);

  const relative = '<svg width="100%" height="auto"><circle r="1"/></svg>';
  assert.equal(normaliseFigure(relative), relative);

  const table = '<table class="question-table"><tr><td>1</td></tr></table>';
  assert.equal(normaliseFigure(table), table);
});

test('a coordinate grid is rendered at its pixel size', () => {
  const out = renderCoordinateGrid({ xEnd: 5, yEnd: 4, step: 1 });

  assert.equal(attribute(out, 'width'), '200');
  assert.equal(attribute(out, 'height'), '160');
  assert.equal(attribute(out, 'viewBox'), '0 0 200 160');
});

test('renderQuestionFigure covers every kind of image a question carries', () => {
  assert.equal(renderQuestionFigure(null), '');
  assert.equal(renderQuestionFigure('null'), '');
  assert.equal(renderQuestionFigure(''), '');
  assert.match(renderQuestionFigure({ xEnd: 3, yEnd: 3, step: 1 }), /class="coordinate-grid/);
  assert.equal(
    attribute(renderQuestionFigure('<svg width="10pt" height="20pt" viewBox="0 0 10 20"></svg>'), 'height'),
    '26.67',
  );
});
