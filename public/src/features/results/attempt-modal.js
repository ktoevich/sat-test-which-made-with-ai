/**
 * Read-only breakdown of an attempt from a history: the student's own, with
 * every question, or another student's, whose answers the API does not send.
 */

import { byId, clear, el, escapeHtml, setHtml } from '../../core/dom.js';
import { sectionName, t } from '../../core/i18n.js';
import { renderMath } from '../../core/katex.js';
import { AnswerStatus, cleanText, hasPassage } from '../../core/questions.js';
import { openModal } from '../../ui/modal.js';
import { describeAnswers, difficultyTag } from './answer-summary.js';
import { renderScoreBubble } from './score-bubble.js';

const BORDER_MODIFIER = {
  [AnswerStatus.CORRECT]: 'attempt-question--correct',
  [AnswerStatus.INCORRECT]: 'attempt-question--incorrect',
  [AnswerStatus.OMITTED]: '',
};

/**
 * @param {{taken_at: string, section?: string, score: number, correct: number, total: number, details?: object[]}} attempt
 * @param {{owner?: {username: string}|null}} [options] the student whose attempt it is, when it is not yours
 */
export function openAttempt(attempt, { owner = null } = {}) {
  const modal = byId('attempt-modal');
  const list = byId('attempt-questions');

  renderScoreBubble(
    { valueEl: byId('attempt-score-value'), fillEl: byId('attempt-score-fill') },
    attempt.score,
  );
  const takenAt = new Date(attempt.taken_at);
  setHtml(
    byId('attempt-summary'),
    `<strong>${escapeHtml(sectionName(attempt.section))}</strong><br>
     <strong>${escapeHtml(t('results_raw'))}</strong> ${escapeHtml(attempt.correct)} / ${escapeHtml(attempt.total)}<br>
     <span>${escapeHtml(
       t('attempt_tested_on', {
         date: Number.isNaN(takenAt.getTime()) ? attempt.taken_at : takenAt.toLocaleString(),
       }),
     )}</span>`,
  );

  clear(list);
  const entries = Array.isArray(attempt.details) ? attempt.details : [];

  if (entries.length === 0) {
    list.append(el('p', { text: owner ? t('attempt_details_private', { name: owner.username }) : t('attempt_no_details') }));
  } else {
    let printedModule = null;
    entries.forEach((entry) => {
      if (printedModule !== entry.module) {
        printedModule = entry.module;
        list.append(el('div', { className: 'module-separator', text: t('module_label', { n: entry.module }) }));
      }
      list.append(questionCard(entry));
    });
  }

  openModal('attempt-modal');
  renderMath(modal);
}

function questionCard(entry) {
  const answers = describeAnswers(entry);
  const card = el('div', {
    className: `attempt-question no-copy ${BORDER_MODIFIER[answers.status]}`.trim(),
  });

  const badge = difficultyTag(entry.question);
  badge.classList.add('attempt-question__difficulty');

  // A Reading and Writing entry shows its passage before the question; both
  // are prose, kept away from the formula renderer.
  const reading = hasPassage(entry.question);
  const passage = reading
    ? el('div', {
        className: 'attempt-question__passage question-passage no-math wrap-text',
        html: entry.question.passage,
      })
    : null;

  card.append(
    ...[
    badge,
    el('div', { className: 'attempt-question__number', text: t('attempt_question', { n: entry.number }) }),
    passage,
    el('div', {
      className: `attempt-question__text wrap-text${reading ? ' no-math' : ''}`,
      html: cleanText(entry.question.text),
    }),
    el('div', {
      className: 'answer-summary',
      html: `<div><strong>${escapeHtml(t('answer_your'))}</strong>
               <span class="${answers.valueClass}">${answers.userHtml}</span></div>
             <div><strong>${escapeHtml(t('answer_correct'))}</strong>
               <span class="answer-value--correct">${answers.correctHtml}</span></div>`,
    }),
    ].filter(Boolean),
  );

  return card;
}
