/** Modal showing one question with its correct answer and rationale. */

import { renderQuestionFigure } from '../../core/coordinate-grid.js';
import { byId, escapeHtml, setHtml, setText, setVisible } from '../../core/dom.js';
import { renderMath } from '../../core/katex.js';
import { t } from '../../core/i18n.js';
import { cleanText, formatParagraphs, hasPassage } from '../../core/questions.js';
import { openModal } from '../../ui/modal.js';
import { describeAnswers } from './answer-summary.js';

const elements = () => ({
  modal: byId('solution-modal'),
  title: byId('solution-title'),
  figure: byId('solution-figure'),
  passage: byId('solution-passage'),
  text: byId('solution-text'),
  rationale: byId('solution-rationale'),
  userAnswer: byId('solution-user-answer'),
  correctAnswer: byId('solution-correct-answer'),
});

/** @param {{module: number, number: number, question: object, userAnswer: string|null}} entry */
export function openSolution(entry) {
  const ui = elements();
  const { question } = entry;
  const answers = describeAnswers(entry);

  setText(ui.title, `${t('module_label', { n: entry.module })}, ${entry.number}`);

  const figure = renderQuestionFigure(question.image);
  setHtml(ui.figure, figure);
  setVisible(ui.figure, Boolean(figure));

  // The prompt is markup, as in the exam: a data table, a formula image, or
  // for Reading and Writing the passage and then the question — prose that
  // the formula renderer must leave alone.
  const reading = hasPassage(question);
  setHtml(ui.passage, reading ? question.passage : '');
  setVisible(ui.passage, reading);
  setHtml(ui.text, reading ? question.text : formatParagraphs(question.text));
  ui.text.classList.toggle('no-math', reading);
  ui.rationale.classList.toggle('no-math', reading);
  ui.userAnswer.parentElement.classList.toggle('no-math', reading);
  renderRationale(ui.rationale, question);

  setHtml(ui.userAnswer, answers.userHtml);
  ui.userAnswer.className = answers.valueClass;
  setHtml(ui.correctAnswer, answers.correctHtml);

  openModal('solution-modal');
  renderMath(ui.modal);
}

function renderRationale(container, question) {
  const rationale = cleanText(question.rationale);
  if (!rationale) {
    setHtml(container, '');
    setVisible(container, false);
    return;
  }

  const skill = question.skill
    ? `<div><span class="skill-badge">Skill: ${escapeHtml(question.skill)}</span></div>`
    : '';
  setHtml(
    container,
    `${skill}<strong class="rationale__title">Rationale:</strong>
     <div class="rationale__body">${rationale}</div>`,
  );
  setVisible(container, true);
}
