/** Shared formatting of "your answer / correct answer" blocks. */

import { el, escapeHtml } from '../../core/dom.js';
import { t } from '../../core/i18n.js';
import { AnswerStatus, QuestionType, optionTextFor, statusOf } from '../../core/questions.js';

const STATUS_KEY = {
  [AnswerStatus.CORRECT]: 'status_correct',
  [AnswerStatus.INCORRECT]: 'status_incorrect',
  [AnswerStatus.OMITTED]: 'status_omitted',
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

const omittedText = () => t('status_omitted');

/**
 * An answer as markup safe to insert. A multiple-choice option comes from the
 * bank and may itself be markup — a formula image, or one of four graphs to
 * choose between — so it is kept as is; a grid-in answer is what the student
 * typed and is escaped.
 */
function answerHtml(question, answer) {
  const text = optionTextFor(question, answer);
  return question.type === QuestionType.MULTIPLE_CHOICE ? text : escapeHtml(text);
}

/** @param {{question: object, userAnswer: string|null}} entry */
export function describeAnswers(entry) {
  const status = statusOf(entry.question, entry.userAnswer);
  const omitted = status === AnswerStatus.OMITTED;
  return {
    status,
    statusLabel: t(STATUS_KEY[status]),
    statusClass: STATUS_CLASS[status],
    valueClass: ANSWER_VALUE_CLASS[status],
    userText: omitted ? omittedText() : optionTextFor(entry.question, entry.userAnswer),
    correctText: optionTextFor(entry.question, entry.question.answer),
    userHtml: omitted ? escapeHtml(omittedText()) : answerHtml(entry.question, entry.userAnswer),
    correctHtml: answerHtml(entry.question, entry.question.answer),
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
