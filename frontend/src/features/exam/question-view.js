/** Renders one question: prompt, optional figure and the answer controls. */

import { renderQuestionFigure } from '../../core/coordinate-grid.js';
import { byId, clear, el, escapeHtml, setHtml, setVisible } from '../../core/dom.js';
import { QuestionType, formatParagraphs, splitOption } from '../../core/questions.js';
import { renderMath } from '../../core/katex.js';

export class QuestionView {
  /**
   * @param {{ onSelectOption: (letter: string) => void,
   *           onToggleEliminate: (letter: string) => void,
   *           onTypeAnswer: (value: string) => void }} handlers
   */
  constructor({ onSelectOption, onToggleEliminate, onTypeAnswer }) {
    this.handlers = { onSelectOption, onToggleEliminate, onTypeAnswer };
    this.elements = {
      figure: byId('question-figure'),
      text: byId('question-text'),
      options: byId('options-list'),
    };
  }

  /** @param {import('./exam-state.js').ExamSession['module']} module */
  render(module) {
    const question = module.currentQuestion;

    this.#renderFigure(question);
    setHtml(
      this.elements.text,
      `<strong>${module.currentIndex + 1}.</strong> ${formatParagraphs(question.text)}`,
    );

    clear(this.elements.options);
    if (question.type === QuestionType.MULTIPLE_CHOICE) {
      this.#renderChoices(question, module);
    } else {
      this.#renderFreeResponse(module);
    }

    renderMath(this.elements.text);
    renderMath(this.elements.options);
  }

  #renderFigure(question) {
    const markup = renderQuestionFigure(question.image);
    setHtml(this.elements.figure, markup);
    setVisible(this.elements.figure, Boolean(markup));
  }

  #renderChoices(question, module) {
    const index = module.currentIndex;
    const selected = module.answerAt(index);
    const eliminated = module.eliminatedAt(index);

    (question.options ?? []).forEach((option) => {
      const { letter, body } = splitOption(option);
      const isEliminated = eliminated.includes(letter);

      const item = el('li', { className: 'option-item' });
      item.classList.toggle('is-selected', selected === letter);
      item.classList.toggle('is-eliminated', isEliminated);

      const content = el('div', {
        className: 'option-item__content',
        html: `<div class="option-item__label">${escapeHtml(letter)}</div>
               <div class="option-item__text wrap-text">${body}</div>`,
      });
      content.addEventListener('click', () => {
        if (!isEliminated) this.handlers.onSelectOption(letter);
      });

      const eliminate = el('button', {
        type: 'button',
        className: 'option-item__eliminate',
        html: `<s>${escapeHtml(letter)}</s>`,
        title: isEliminated ? `Restore option ${letter}` : `Cross out option ${letter}`,
      });
      eliminate.addEventListener('click', (event) => {
        event.stopPropagation();
        this.handlers.onToggleEliminate(letter);
      });

      item.append(content, eliminate);
      this.elements.options.append(item);
    });
  }

  #renderFreeResponse(module) {
    const current = module.answerAt(module.currentIndex);
    const input = el('input', {
      type: 'text',
      className: 'field field--answer',
      placeholder: 'Enter your answer...',
    });
    input.value = current ?? '';
    input.addEventListener('input', (event) => this.handlers.onTypeAnswer(event.target.value));
    // Enter would submit nothing useful here; keep the focus in the field.
    input.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') event.preventDefault();
    });

    this.elements.options.append(el('div', { className: 'spr-answer' }, [input]));
  }
}
