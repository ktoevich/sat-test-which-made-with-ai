/** Read-only breakdown of an attempt loaded from the user's saved history. */

import { byId, clear, el, escapeHtml, setHtml } from '../../core/dom.js';
import { renderMath } from '../../core/katex.js';
import { AnswerStatus, cleanText } from '../../core/questions.js';
import { openModal } from '../../ui/modal.js';
import { describeAnswers, difficultyTag } from './answer-summary.js';
import { renderScoreBubble } from './score-bubble.js';

const BORDER_MODIFIER = {
  [AnswerStatus.CORRECT]: 'attempt-question--correct',
  [AnswerStatus.INCORRECT]: 'attempt-question--incorrect',
  [AnswerStatus.OMITTED]: '',
};

/** @param {{taken_at: string, score: number, correct: number, total: number, details: object[]}} attempt */
export function openAttempt(attempt) {
  const modal = byId('attempt-modal');
  const list = byId('attempt-questions');

  renderScoreBubble(
    { valueEl: byId('attempt-score-value'), fillEl: byId('attempt-score-fill') },
    attempt.score,
  );
  const takenAt = new Date(attempt.taken_at);
  setHtml(
    byId('attempt-summary'),
    `<strong>Raw Score:</strong> ${escapeHtml(attempt.correct)} / ${escapeHtml(attempt.total)} correct<br>
     <span>Tested on: ${escapeHtml(
       Number.isNaN(takenAt.getTime()) ? attempt.taken_at : takenAt.toLocaleString(),
     )}</span>`,
  );

  clear(list);
  const entries = Array.isArray(attempt.details) ? attempt.details : [];

  if (entries.length === 0) {
    list.append(el('p', { text: 'No detailed data was saved for this attempt.' }));
  } else {
    let printedModule = null;
    entries.forEach((entry) => {
      if (printedModule !== entry.module) {
        printedModule = entry.module;
        list.append(el('div', { className: 'module-separator', text: `Module ${entry.module}` }));
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

  card.append(
    badge,
    el('div', { className: 'attempt-question__number', text: `Question ${entry.number}` }),
    el('div', {
      className: 'attempt-question__text wrap-text',
      html: cleanText(entry.question.text),
    }),
    el('div', {
      className: 'answer-summary',
      html: `<div><strong>Your Answer:</strong>
               <span class="${answers.valueClass}">${escapeHtml(answers.userText)}</span></div>
             <div><strong>Correct Answer:</strong>
               <span class="answer-value--correct">${escapeHtml(answers.correctText)}</span></div>`,
    }),
  );

  return card;
}
