/** Drives an attempt: loads modules, handles navigation and submission. */

import { DEFAULT_SECTION, sectionOf } from '../../config.js';
import { ApiError } from '../../api/client.js';
import { fetchModule1, fetchModule2 } from '../../api/exam-api.js';
import { byId, setText, setVisible } from '../../core/dom.js';
import { nextModuleTarget } from '../../core/scoring.js';
import { hideLoading, runCountdown, showLoading } from '../../ui/loading-overlay.js';
import { closeModal, openModal } from '../../ui/modal.js';
import { ExamCalculator } from './calculator.js';
import { ExamSession } from './exam-state.js';
import { ExamTimer } from './timer.js';
import { QuestionMap } from './question-map.js';
import { QuestionView } from './question-view.js';

const FINISH_MODAL_ID = 'finish-modal';

export class ExamController {
  /**
   * @param {{ onFinished: (session: ExamSession) => void,
   *           onUnavailable: (message: string) => void }} handlers
   */
  constructor({ onFinished, onUnavailable }) {
    this.onFinished = onFinished;
    this.onUnavailable = onUnavailable;
    this.session = new ExamSession();

    this.view = new QuestionView({
      onSelectOption: (letter) => this.#selectOption(letter),
      onToggleEliminate: (letter) => this.#toggleEliminate(letter),
      onTypeAnswer: (value) => this.#typeAnswer(value),
    });
    this.map = new QuestionMap({ onSelect: (index) => this.#goTo(index) });
    this.timer = new ExamTimer({ onExpire: () => this.#submitModule() });
    this.calculator = new ExamCalculator();

    this.elements = {
      sectionInfo: byId('section-info'),
      calculatorButton: byId('calculator-btn'),
      prev: byId('prev-btn'),
      next: byId('next-btn'),
      flag: byId('flag-btn'),
    };

    this.#bindEvents();
  }

  #bindEvents() {
    this.elements.prev.addEventListener('click', () => this.#goTo(this.#index - 1));
    this.elements.next.addEventListener('click', () => {
      if (this.#index < this.#module.size - 1) this.#goTo(this.#index + 1);
      else openModal(FINISH_MODAL_ID);
    });
    this.elements.flag.addEventListener('click', () => {
      this.#module.toggleFlag(this.#index);
      this.#renderCurrent();
    });
    byId('finish-confirm-btn').addEventListener('click', () => {
      closeModal(FINISH_MODAL_ID);
      this.#submitModule();
    });
  }

  get #module() {
    return this.session.module;
  }

  get #index() {
    return this.#module.currentIndex;
  }

  get #section() {
    return sectionOf(this.session.section);
  }

  /**
   * Fetch module 1 of a section and start the attempt.
   * @param {string} section `math` or `reading`
   * @returns {Promise<boolean>} false when no test could be started.
   */
  async startAttempt(section = DEFAULT_SECTION) {
    showLoading('Checking for available tests');
    try {
      const payload = await fetchModule1(section);
      this.session.start(payload.test_id, payload.questions, payload.section ?? section);
      await this.#beginModule(1);
      return true;
    } catch (error) {
      hideLoading();
      this.onUnavailable(ExamController.#messageFor(error, 'Could not load Module 1.'));
      return false;
    }
  }

  async #loadModule2(target) {
    showLoading('Module 2 is loading');
    try {
      const payload = await fetchModule2({ testId: this.session.testId, target });
      this.session.advanceTo(2, payload.questions);
      await this.#beginModule(2);
    } catch (error) {
      hideLoading();
      this.onUnavailable(ExamController.#messageFor(error, 'Could not load Module 2.'));
    }
  }

  async #beginModule(number) {
    const section = this.#section;
    setText(this.elements.sectionInfo, `${section.label}: Module ${number}`);
    this.map.build(this.#module.size);
    // Only the math section offers the calculator, as on the real test.
    this.calculator.reset();
    setVisible(this.elements.calculatorButton, section.calculator);
    await runCountdown();
    this.#renderCurrent();
    this.timer.start(section.minutes * 60);
  }

  #goTo(index) {
    if (index < 0 || index >= this.#module.size) return;
    this.#module.currentIndex = index;
    this.#renderCurrent();
  }

  #selectOption(letter) {
    this.#module.setAnswer(this.#index, letter);
    this.#renderCurrent();
  }

  #toggleEliminate(letter) {
    this.#module.toggleEliminated(this.#index, letter);
    this.#renderCurrent();
  }

  #typeAnswer(value) {
    // Do not re-render: that would drop focus out of the input mid-typing.
    this.#module.setAnswer(this.#index, value);
    this.map.update(this.#module);
  }

  #renderCurrent() {
    const module = this.#module;
    this.view.render(module);
    this.map.update(module);

    this.elements.flag.classList.toggle('is-flagged', module.isFlagged(module.currentIndex));
    this.elements.prev.disabled = module.currentIndex === 0;
    setText(
      this.elements.next,
      module.currentIndex === module.size - 1 ? 'Finish' : 'Next',
    );
  }

  #submitModule() {
    this.timer.stop();
    this.map.close();
    this.calculator.close();
    const score = this.session.finishModule();

    if (this.#module.number === 1) {
      this.#loadModule2(nextModuleTarget(score.correct, score.total, this.#section.passMark));
      return;
    }
    this.onFinished(this.session);
  }

  static #messageFor(error, fallback) {
    if (error instanceof ApiError) return error.message;
    console.error(error);
    return fallback;
  }
}
