/** Shared formatting of "your answer / correct answer" blocks. */

import { el } from '../../core/dom.js';
import { AnswerStatus, optionTextFor, statusOf } from '../../core/questions.js';

const STATUS_LABEL = {
  [AnswerStatus.CORRECT]: 'Correct',
  [AnswerStatus.INCORRECT]: 'Incorrect',
  [AnswerStatus.OMITTED]: 'Omitted',
};

const STATUS_CLASS = {
  [AnswerStatus.CORRECT]: 'status-badge--correct',
  [AnswerStatus.INCORRECT]: 'status-badge--incorrect',
  [AnswerStatus.OMITTED]: 'status-badge--omitted',
};

const ANSWER_VALUE_CLASS = {
  [AnswerStatus.CORRECT]: 'answer-value--correct',
  [AnswerStatus.INCORRECT]: 'answer-value--incorrect',
  [AnswerStatus.OMITTED]: 'answer-value--omitted',
};

export const OMITTED_TEXT = 'Omitted (No answer)';

/** @param {{question: object, userAnswer: string|null}} entry */
export function describeAnswers(entry) {
  const status = statusOf(entry.question, entry.userAnswer);
  return {
    status,
    statusLabel: STATUS_LABEL[status],
    statusClass: STATUS_CLASS[status],
    valueClass: ANSWER_VALUE_CLASS[status],
    userText:
      status === AnswerStatus.OMITTED ? OMITTED_TEXT : optionTextFor(entry.question, entry.userAnswer),
    correctText: optionTextFor(entry.question, entry.question.answer),
  };
}

export function statusBadge(entry) {
  const { statusLabel, statusClass } = describeAnswers(entry);
  return el('span', { className: `status-badge ${statusClass}`, text: statusLabel });
}

export function difficultyTag(question) {
  const difficulty = String(question.difficulty ?? 'Medium');
  return el('span', {
    className: `diff-tag diff-tag--${difficulty.toLowerCase()}`,
    text: difficulty,
  });
}
