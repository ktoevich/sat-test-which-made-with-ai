/** Raw-score counting and the conversion to a scaled SAT score. */

import { ADAPTIVE_PASS_MARK, SCORE_MAX, SCORE_MIN } from '../config.js';
import { AnswerStatus, statusOf } from './questions.js';

export function countCorrect(questions, answers) {
  return questions.reduce(
    (total, question, index) =>
      statusOf(question, answers[index]) === AnswerStatus.CORRECT ? total + 1 : total,
    0,
  );
}

/**
 * Map a raw score onto the 200-800 scale, rounded to the nearest 10 the way
 * official score reports are.
 */
export function toScaledScore(correct, total) {
  if (!total) return SCORE_MIN;
  if (correct <= 0) return SCORE_MIN;
  if (correct >= total) return SCORE_MAX;
  const span = SCORE_MAX - SCORE_MIN;
  return Math.round((SCORE_MIN + (correct / total) * span) / 10) * 10;
}

/** How full the score bubble should be, as a percentage. */
export function scoreFillPercent(score) {
  const ratio = (Number(score) - SCORE_MIN) / (SCORE_MAX - SCORE_MIN);
  return Math.min(100, Math.max(0, ratio * 100));
}

/** Module 2 is harder only when module 1 went well enough (15 of 22 or better). */
export function nextModuleTarget(correct, total) {
  if (!total) return 'LOWER';
  const needed = Math.ceil((total * ADAPTIVE_PASS_MARK.correct) / ADAPTIVE_PASS_MARK.outOf);
  return correct >= needed ? 'HIGHER' : 'LOWER';
}
