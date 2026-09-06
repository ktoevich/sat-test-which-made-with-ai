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
    this.module = null;
    /** @type {{module: number, number: number, question: object, userAnswer: string|null}[]} */
    this.review = [];
    /** @type {Record<number, {correct: number, total: number}>} */
    this.moduleScores = {};
  }

  /** Begin a fresh attempt with module 1. */
  start(testId, questions) {
    this.testId = testId;
    this.review = [];
    this.moduleScores = {};
    this.module = new ModuleState(1, questions);
    return this.module;
  }

  /** Continue the same attempt with module 2. */
  advanceTo(moduleNumber, questions) {
    this.module = new ModuleState(moduleNumber, questions);
    return this.module;
  }

  /** Score the current module and append its questions to the review list. */
  finishModule() {
    const { number, questions, answers } = this.module;
    const correct = countCorrect(questions, answers);

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
