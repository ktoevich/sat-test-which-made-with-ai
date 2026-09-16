/** In-memory state of a single attempt: two modules and their answers. */

import { countCorrect } from '../../core/scoring.js';

class ModuleState {
  constructor(number, questions) {
    this.number = number;
    this.questions = questions;
    this.answers = new Array(questions.length).fill(null);
    this.flags = new Array(questions.length).fill(false);
    this.eliminated = questions.map(() => []);
    this.currentIndex = 0;
  }

  get size() {
    return this.questions.length;
  }

  get currentQuestion() {
    return this.questions[this.currentIndex];
  }

  answerAt(index) {
    return this.answers[index];
  }

  setAnswer(index, value) {
    this.answers[index] = value;
  }

  isFlagged(index) {
    return this.flags[index];
  }

  toggleFlag(index) {
    this.flags[index] = !this.flags[index];
  }

  eliminatedAt(index) {
    return this.eliminated[index];
  }

  toggleEliminated(index, letter) {
    const current = this.eliminated[index];
    if (current.includes(letter)) {
      this.eliminated[index] = current.filter((item) => item !== letter);
      return;
    }
    current.push(letter);
    // A struck-through option can no longer be the selected answer.
    if (this.answers[index] === letter) this.answers[index] = null;
  }
}

export class ExamSession {
  constructor() {
    this.testId = null;
    /** @type {string} the section key: `math` or `reading` */
    this.section = 'math';
    /** @type {string} the module 2 route, once chosen: HIGHER or LOWER */
    this.target = '';
    /** Seconds spent in finished modules, plus when the running one started. */
    this.timeSpent = 0;
    this.moduleStartedAt = null;
    this.module = null;
    /** @type {{module: number, number: number, question: object, userAnswer: string|null}[]} */
    this.review = [];
    /** @type {Record<number, {correct: number, total: number}>} */
    this.moduleScores = {};
  }

  /** Begin a fresh attempt of one section with module 1. */
  start(testId, questions, section = 'math') {
    this.testId = testId;
    this.section = section;
    this.target = '';
    this.timeSpent = 0;
    this.moduleStartedAt = null;
    this.review = [];
    this.moduleScores = {};
    this.module = new ModuleState(1, questions);
    return this.module;
  }

  /** Continue the same attempt with module 2. */
  advanceTo(moduleNumber, questions, target = '') {
    if (target) this.target = target;
    this.module = new ModuleState(moduleNumber, questions);
    return this.module;
  }

  /** The clock starts when the questions appear, not while the countdown runs. */
  startClock(now = Date.now()) {
    this.moduleStartedAt = now;
  }

  /** Score the current module and append its questions to the review list. */
  finishModule(now = Date.now()) {
    const { number, questions, answers } = this.module;
    const correct = countCorrect(questions, answers);
    if (this.moduleStartedAt) {
      this.timeSpent += Math.max(0, Math.round((now - this.moduleStartedAt) / 1000));
      this.moduleStartedAt = null;
    }

    this.moduleScores[number] = { correct, total: questions.length };
    questions.forEach((question, index) => {
      this.review.push({
        module: number,
        number: index + 1,
        question,
        userAnswer: answers[index],
      });
    });

    return this.moduleScores[number];
  }

  /** Everything needed to finish this attempt on another page load. */
  snapshot() {
    const module = this.module;
    return {
      testId: this.testId,
      section: this.section,
      target: this.target,
      timeSpent: this.timeSpent,
      moduleStartedAt: this.moduleStartedAt,
      review: this.review,
      moduleScores: this.moduleScores,
      module: module && {
        number: module.number,
        questions: module.questions,
        answers: module.answers,
        flags: module.flags,
        eliminated: module.eliminated,
        currentIndex: module.currentIndex,
      },
    };
  }

  /** Rebuild a session from a snapshot; the running module keeps its answers. */
  static fromSnapshot(snapshot) {
    const session = new ExamSession();
    session.testId = snapshot.testId;
    session.section = snapshot.section ?? 'math';
    session.target = snapshot.target ?? '';
    session.timeSpent = snapshot.timeSpent ?? 0;
    session.moduleStartedAt = snapshot.moduleStartedAt ?? null;
    session.review = snapshot.review ?? [];
    session.moduleScores = snapshot.moduleScores ?? {};
    if (snapshot.module) {
      const module = new ModuleState(snapshot.module.number, snapshot.module.questions);
      module.answers = snapshot.module.answers ?? module.answers;
      module.flags = snapshot.module.flags ?? module.flags;
      module.eliminated = snapshot.module.eliminated ?? module.eliminated;
      module.currentIndex = snapshot.module.currentIndex ?? 0;
      session.module = module;
    }
    return session;
  }

  get totals() {
    return Object.values(this.moduleScores).reduce(
      (totals, score) => ({
        correct: totals.correct + score.correct,
        total: totals.total + score.total,
      }),
      { correct: 0, total: 0 },
    );
  }
}
