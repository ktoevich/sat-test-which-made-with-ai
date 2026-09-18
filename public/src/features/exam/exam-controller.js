/** Drives an attempt: loads modules, handles navigation and submission. */

import { DEFAULT_SECTION, sectionOf } from '../../config.js';
import { ApiError } from '../../api/client.js';
import { fetchModule1, fetchModule2 } from '../../api/exam-api.js';
import { byId, setText, setVisible } from '../../core/dom.js';
import { sectionName, t } from '../../core/i18n.js';
import { nextModuleTarget } from '../../core/scoring.js';
import { hideLoading, runCountdown, showLoading } from '../../ui/loading-overlay.js';
import { closeModal, openModal } from '../../ui/modal.js';
import { ExamCalculator } from './calculator.js';
import { ExamSession } from './exam-state.js';
import { activeTestStore, installReloadGuard } from './reload-guard.js';
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
    /** True while a module is on screen and the clock runs. */
    this.active = false;

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
    installReloadGuard({
      isActive: () => this.active,
      onFinishNow: () => this.terminate(),
    });
    document.addEventListener('languagechange', () => {
      if (this.active) {
        this.#labelModule();
        this.#renderCurrent();
      }
    });
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
      this.#persist();
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
   * @param {{ testId?: string }} [options] a specific test, to retake it
   * @returns {Promise<boolean>} false when no test could be started.
   */
  async startAttempt(section = DEFAULT_SECTION, { testId } = {}) {
    showLoading(t('loading_checking'));
    try {
      const payload = await fetchModule1(section, { testId });
      this.session.start(payload.test_id, payload.questions, payload.section ?? section);
      await this.#beginModule(1);
      return true;
    } catch (error) {
      hideLoading();
      this.onUnavailable(ExamController.#messageFor(error, t('exam_module_failed', { n: 1 })));
      return false;
    }
  }

  async #loadModule2(target) {
    showLoading(t('loading_module', { n: 2 }));
    try {
      const payload = await fetchModule2({ testId: this.session.testId, target });
      this.session.advanceTo(2, payload.questions, target);
      await this.#beginModule(2);
    } catch (error) {
      hideLoading();
      this.onUnavailable(ExamController.#messageFor(error, t('exam_module_failed', { n: 2 })));
    }
  }

  #labelModule() {
    setText(
      this.elements.sectionInfo,
      t('exam_module', { section: sectionName(this.session.section), n: this.#module.number }),
    );
  }

  async #beginModule(number) {
    const section = this.#section;
    this.#labelModule();
    this.map.build(this.#module.size);
    // Only the math section offers the calculator, as on the real test.
    this.calculator.reset();
    setVisible(this.elements.calculatorButton, section.calculator);
    await runCountdown();
    this.session.startClock();
    this.active = true;
    this.#renderCurrent();
    this.#persist();
    this.timer.start(section.minutes * 60);
  }

  /** Mirror the attempt into session storage, so a reload can still finish it. */
  #persist() {
    if (this.active) activeTestStore.write(this.session.snapshot());
  }

  /**
   * End the test now, from the reload warning: what was not answered counts
   * as omitted. In module 1 the second module is fetched and counted as
   * omitted too, so the attempt is scored out of the full test.
   */
  async terminate() {
    if (!this.active) return;
    this.timer.stop();
    this.map.close();
    this.calculator.close();
    this.active = false;
    activeTestStore.clear();
    const score = this.session.finishModule();
    if (this.#module.number === 1) {
      const target = nextModuleTarget(score.correct, score.total, this.#section.passMark);
      try {
        const payload = await fetchModule2({ testId: this.session.testId, target });
        this.session.advanceTo(2, payload.questions, target);
        this.session.finishModule();
      } catch {
        // Without module 2 the attempt is scored on module 1 alone.
      }
    }
    this.onFinished(this.session, { terminated: true });
  }

  /** A test that was running when the page last unloaded: finish it as it stands. */
  async resumeTerminated(snapshot) {
    try {
      this.session = ExamSession.fromSnapshot(snapshot);
    } catch {
      activeTestStore.clear();
      return false;
    }
    if (!this.session.module) {
      activeTestStore.clear();
      return false;
    }
    this.active = true;
    await this.terminate();
    return true;
  }

  #goTo(index) {
    if (index < 0 || index >= this.#module.size) return;
    this.#module.currentIndex = index;
    this.#renderCurrent();
    this.#persist();
  }

  #selectOption(letter) {
    this.#module.setAnswer(this.#index, letter);
    this.#renderCurrent();
    this.#persist();
  }

  #toggleEliminate(letter) {
    this.#module.toggleEliminated(this.#index, letter);
    this.#renderCurrent();
    this.#persist();
  }

  #typeAnswer(value) {
    // Do not re-render: that would drop focus out of the input mid-typing.
    this.#module.setAnswer(this.#index, value);
    this.map.update(this.#module);
    this.#persist();
  }

  #renderCurrent() {
    const module = this.#module;
    this.view.render(module);
    this.map.update(module);

    this.elements.flag.classList.toggle('is-flagged', module.isFlagged(module.currentIndex));
    this.elements.prev.disabled = module.currentIndex === 0;
    setText(
      this.elements.next,
      module.currentIndex === module.size - 1 ? t('exam_finish') : t('exam_next'),
    );
  }

  #submitModule() {
    this.timer.stop();
    this.map.close();
    this.calculator.close();
    this.active = false;
    activeTestStore.clear();
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
