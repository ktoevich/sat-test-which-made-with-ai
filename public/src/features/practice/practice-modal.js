/**
 * Practising one domain: a few questions from the bank, each checked the
 * moment it is answered, with the solution shown before the next one.
 */

import { ApiError } from '../../api/client.js';
import { fetchPracticeSet } from '../../api/practice-api.js';
import { renderQuestionFigure } from '../../core/coordinate-grid.js';
import { byId, clear, el, escapeHtml, setHtml, setText, setVisible } from '../../core/dom.js';
import { t } from '../../core/i18n.js';
import { renderMath } from '../../core/katex.js';
import { QuestionType, formatParagraphs, hasPassage, matchesAnswer, optionTextFor, splitOption } from '../../core/questions.js';
import { closeModal, openModal } from '../../ui/modal.js';

const COUNT = 5;

export class PracticeModal {
  constructor() {
    this.questions = [];
    this.index = 0;
    this.answer = null;
    this.right = 0;
    this.section = 'math';
    this.domain = '';
    this.elements = {
      title: byId('practice-title'),
      progress: byId('practice-progress'),
      body: byId('practice-body'),
      figure: byId('practice-figure'),
      passage: byId('practice-passage'),
      text: byId('practice-text'),
      options: byId('practice-options'),
      feedback: byId('practice-feedback'),
      check: byId('practice-check'),
      next: byId('practice-next'),
      finish: byId('practice-finish'),
    };
    byId('practice-close').addEventListener('click', () => this.close());
    this.elements.finish.addEventListener('click', () => this.close());
    this.elements.check.addEventListener('click', () => this.#check());
    this.elements.next.addEventListener('click', () => this.#next());
  }

  async open(section, domain) {
    this.section = section;
    this.domain = domain;
    this.index = 0;
    this.right = 0;
    this.questions = [];
    setText(this.elements.title, t('practice_title', { domain }));
    setText(this.elements.progress, t('practice_loading'));
    this.#showQuestionArea(true);
    clear(this.elements.options);
    setHtml(this.elements.text, '');
    setVisible(this.elements.figure, false);
    setVisible(this.elements.passage, false);
    setVisible(this.elements.feedback, false);
    openModal('practice-modal');
    try {
      const { questions } = await fetchPracticeSet({ section, domain, count: COUNT });
      this.questions = questions;
    } catch (error) {
      setText(this.elements.progress, error instanceof ApiError ? error.message : t('practice_empty'));
      return;
    }
    if (!this.questions.length) {
      setText(this.elements.progress, t('practice_empty'));
      return;
    }
    this.#render();
  }

  close() {
    closeModal('practice-modal');
  }

  #showQuestionArea(visible) {
    const summary = this.elements.body.querySelector('.practice__done');
    summary?.remove();
    ['figure', 'passage', 'text', 'options', 'feedback'].forEach((key) => {
      if (!visible) this.elements[key].classList.add('hidden');
    });
    if (visible) {
      this.elements.text.classList.remove('hidden');
      this.elements.options.classList.remove('hidden');
    }
    setVisible(this.elements.check, visible);
    setVisible(this.elements.next, false);
  }

  #render() {
    const question = this.questions[this.index];
    const { figure, passage, text, options, feedback, check, next, progress } = this.elements;
    this.answer = null;
    setText(progress, t('practice_progress', { n: this.index + 1, total: this.questions.length }));

    const markup = renderQuestionFigure(question.image);
    setHtml(figure, markup);
    setVisible(figure, Boolean(markup));

    const reading = hasPassage(question);
    setHtml(passage, reading ? question.passage : '');
    setVisible(passage, reading);
    text.classList.toggle('no-math', reading);
    options.classList.toggle('no-math', reading);
    setHtml(text, `<strong>${this.index + 1}.</strong> ${reading ? question.text : formatParagraphs(question.text)}`);

    clear(options);
    if (question.type === QuestionType.MULTIPLE_CHOICE) {
      (question.options ?? []).forEach((option) => {
        const { letter, body } = splitOption(option);
        const item = el('li', { className: 'option-item', dataset: { letter } });
        const content = el('div', {
          className: 'option-item__content',
          html: `<div class="option-item__label">${escapeHtml(letter)}</div><div class="option-item__text wrap-text">${body}</div>`,
        });
        content.addEventListener('click', () => {
          if (this.elements.next.classList.contains('hidden') === false) return; // already checked
          this.answer = letter;
          options.querySelectorAll('.option-item').forEach((li) => li.classList.toggle('is-selected', li === item));
        });
        item.append(content);
        options.append(item);
      });
    } else {
      const input = el('input', { type: 'text', className: 'field field--answer', placeholder: t('exam_answer_placeholder') });
      input.addEventListener('input', () => { this.answer = input.value; });
      input.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') { event.preventDefault(); this.#check(); }
      });
      options.append(el('div', { className: 'spr-answer' }, [input]));
      setTimeout(() => input.focus(), 0);
    }

    setVisible(feedback, false);
    setVisible(check, true);
    setVisible(next, false);
    if (!reading) {
      renderMath(text);
      renderMath(options);
    }
  }

  #check() {
    const question = this.questions[this.index];
    if (!question) return;
    const { feedback, check, next, options } = this.elements;
    if (this.answer === null || String(this.answer).trim() === '') {
      setHtml(feedback, `<span class="practice__verdict">${escapeHtml(t('practice_pick'))}</span>`);
      feedback.className = 'practice__feedback';
      setVisible(feedback, true);
      return;
    }
    const correct = matchesAnswer(question, this.answer);
    if (correct) this.right += 1;
    const correctText = question.type === QuestionType.MULTIPLE_CHOICE ? optionTextFor(question, question.answer) : escapeHtml(question.answer);
    const rationale = String(question.rationale ?? '');
    const reading = hasPassage(question);
    feedback.className = `practice__feedback ${correct ? 'practice__feedback--right' : 'practice__feedback--wrong'}${reading ? ' no-math' : ''}`;
    setHtml(
      feedback,
      `<span class="practice__verdict">${correct ? '✅ ' + escapeHtml(t('practice_correct')) : '❌ ' + t('practice_incorrect', { answer: correctText })}</span>` +
        (rationale ? `<div class="rationale__body">${rationale}</div>` : ''),
    );
    setVisible(feedback, true);
    options.querySelectorAll('.option-item').forEach((li) => {
      const letter = li.dataset.letter;
      if (letter === String(question.answer).toUpperCase()) li.classList.add('is-right');
      else if (letter === this.answer && !correct) li.classList.add('is-wrong');
    });
    setVisible(check, false);
    setVisible(next, true);
    if (!reading) renderMath(feedback);
  }

  #next() {
    this.index += 1;
    if (this.index < this.questions.length) {
      this.#render();
      return;
    }
    this.#showQuestionArea(false);
    setText(this.elements.progress, '');
    this.elements.body.append(
      el('div', { className: 'practice__done' }, [
        el('div', { text: '🎉', style: 'font-size:3rem' }),
        el('h3', { text: t('practice_done_title') }),
        el('p', { text: t('practice_done_body', { right: this.right, total: this.questions.length, domain: this.domain }) }),
      ]),
    );
  }
}
