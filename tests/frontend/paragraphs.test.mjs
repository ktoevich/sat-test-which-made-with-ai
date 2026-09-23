/**
 * How a math prompt's line breaks reach the page. A prompt can open with a
 * table written as indented markup, and its line breaks are not paragraphs.
 */

import assert from 'node:assert/strict';
import test from 'node:test';

import { formatParagraphs } from '../../public/src/core/questions.js';

test('a line break in the prose is a paragraph break', () => {
  assert.equal(formatParagraphs('First.\nSecond.'), 'First.<br><br>Second.');
});

test('a table keeps its markup and adds no breaks', () => {
  const text = '<table class="question-table">\n\t<tbody>\n\t\t<tr>\n\t\t\t<td>1</td>\n'
    + '\t\t\t<td>4</td>\n\t\t</tr>\n\t</tbody>\n</table>\nIn the table above, what is $k$?';
  assert.equal(
    formatParagraphs(text),
    '<table class="question-table"><tbody><tr><td>1</td><td>4</td></tr></tbody></table>'
      + 'In the table above, what is $k$?',
  );
});

test('the text inside a table cell is left alone', () => {
  const text = '<table><tr><td>Employee A </td><td>1 Star</td></tr></table>';
  assert.equal(formatParagraphs(text), text);
});
