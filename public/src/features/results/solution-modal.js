/** Modal showing one question with its correct answer and rationale. */

import { renderQuestionFigure } from '../../core/coordinate-grid.js';
import { byId, escapeHtml, setHtml, setText, setVisible } from '../../core/dom.js';
import { renderMath } from '../../core/katex.js';
import { cleanText } from '../../core/questions.js';
import { openModal } from '../../ui/modal.js';
import { describeAnswers } from './answer-summary.js';

const elements = () => ({
  modal: byId('solution-modal'),
  title: byId('solution-title'),
  figure: byId('solution-figure'),
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

  const idSuffix = question.question_id
    ? ` <span class="modal__id">(ID: ${escapeHtml(question.question_id)})</span>`
    : '';
  setHtml(ui.title, `Module ${entry.module}, Question ${entry.number}${idSuffix}`);

  const figure = renderQuestionFigure(question.image);
  setHtml(ui.figure, figure);
  setVisible(ui.figure, Boolean(figure));

  setText(ui.text, cleanText(question.text));
  renderRationale(ui.rationale, question);

  setText(ui.userAnswer, answers.userText);
  ui.userAnswer.className = answers.valueClass;
  setText(ui.correctAnswer, answers.correctText);

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
