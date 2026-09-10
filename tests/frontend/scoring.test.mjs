/**
 * How a grid-in answer is marked. The bank lists several right spellings for
 * one answer — 0.25 and 1/4 are the same — and a student who writes it a third
 * equivalent way must not be failed for it.
 */

import assert from 'node:assert/strict';
import test from 'node:test';

import {
  AnswerStatus, acceptedAnswers, matchesAnswer, statusOf,
} from '../../public/src/core/questions.js';

const gridIn = (answer, accepted) => ({
  type: 'SPR',
  answer,
  ...(accepted ? { accepted_answers: accepted } : {}),
});

test('the answer the bank stores is accepted', () => {
  assert.equal(statusOf(gridIn('12'), '12'), AnswerStatus.CORRECT);
  assert.equal(statusOf(gridIn('12'), ' 12 '), AnswerStatus.CORRECT);
  assert.equal(statusOf(gridIn('12'), '13'), AnswerStatus.INCORRECT);
  assert.equal(statusOf(gridIn('12'), ''), AnswerStatus.OMITTED);
});

test('every alternative the bank lists is accepted too', () => {
  const question = gridIn('0.25', ['1/4']);
  assert.deepEqual(acceptedAnswers(question), ['0.25', '1/4']);
  for (const given of ['0.25', '1/4', '.25']) {
    assert.equal(statusOf(question, given), AnswerStatus.CORRECT, given);
  }
  assert.equal(statusOf(question, '0.26'), AnswerStatus.INCORRECT);
});

test('the same number written another way is still right', () => {
  assert.ok(matchesAnswer(gridIn('0.5'), '.5'));
  assert.ok(matchesAnswer(gridIn('0.5'), '1/2'));
  assert.ok(matchesAnswer(gridIn('1/2'), '0.5'));
  assert.ok(matchesAnswer(gridIn('8.6'), '43/5'));
  assert.ok(matchesAnswer(gridIn('-3'), '-3.0'));
  assert.ok(matchesAnswer(gridIn('1200'), '1,200'));
});

test('a rounded answer is accepted to the four places the bank rounds to', () => {
  const question = gridIn('.1764', ['.1765', '3/17']);
  for (const given of ['.1764', '.1765', '3/17', '0.1765']) {
    assert.equal(statusOf(question, given), AnswerStatus.CORRECT, given);
  }
  assert.equal(statusOf(question, '0.18'), AnswerStatus.INCORRECT);
});

test('a near miss is still a miss', () => {
  assert.ok(!matchesAnswer(gridIn('0.5'), '0.6'));
  assert.ok(!matchesAnswer(gridIn('1/2'), '2/1'));
  assert.ok(!matchesAnswer(gridIn('12'), 'twelve'));
  assert.ok(!matchesAnswer(gridIn('1/2'), '1/0'), 'a zero denominator must not match');
});

test('multiple choice is unaffected', () => {
  const mcq = { type: 'MCQ', answer: 'B', options: ['A) 1', 'B) 2', 'C) 3', 'D) 4'] };
  assert.equal(statusOf(mcq, 'b'), AnswerStatus.CORRECT);
  assert.equal(statusOf(mcq, 'C'), AnswerStatus.INCORRECT);
});
