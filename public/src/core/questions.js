/** Pure helpers for reading question objects returned by the API. */

export const QuestionType = {
  MULTIPLE_CHOICE: 'MCQ',
  STUDENT_RESPONSE: 'SPR',
};

export const AnswerStatus = {
  CORRECT: 'correct',
  INCORRECT: 'incorrect',
  OMITTED: 'omitted',
};

/**
 * Normalise question or rationale text coming from the bank.
 * The bank occasionally carries trailing whitespace and stray markers.
 */
export function cleanText(text) {
  return String(text ?? '').trim();
}

/** Turn newlines into paragraph breaks for display. */
export function formatParagraphs(text) {
  return cleanText(text).replace(/\n/g, '<br><br>');
}

/** Answers are compared case- and whitespace-insensitively. */
export function normaliseAnswer(answer) {
  if (answer === null || answer === undefined) return '';
  return String(answer).trim().toUpperCase();
}

export function isAnswered(answer) {
  return normaliseAnswer(answer) !== '';
}

/**
 * A grid-in answer as a number, or null when it is not one.
 * Accepts a decimal, a leading-dot decimal and a simple fraction — the three
 * forms the answer sheet allows.
 */
function asNumber(answer) {
  const text = normaliseAnswer(answer).replace(/\s+/g, '').replace(/,/g, '');
  if (/^-?(?:\d+\.?\d*|\.\d+)$/.test(text)) return Number(text);
  const fraction = /^(-?\d+)\/(\d+)$/.exec(text);
  if (fraction && Number(fraction[2]) !== 0) return Number(fraction[1]) / Number(fraction[2]);
  return null;
}

/**
 * Every form of a question's answer that should be marked right.
 * `accepted_answers` carries the alternatives the bank lists for a grid-in —
 * `0.25` and `1/4` are the same answer, and so are `.1764` and `3/17`.
 */
export function acceptedAnswers(question) {
  return [question.answer, ...(question.accepted_answers ?? [])].filter(isAnswered);
}

export function matchesAnswer(question, userAnswer) {
  const given = normaliseAnswer(userAnswer);
  const accepted = acceptedAnswers(question);
  if (accepted.some((answer) => normaliseAnswer(answer) === given)) return true;

  // Written a different way but the same number: 1/2 for 0.5, .5 for 0.5.
  const value = asNumber(given);
  if (value === null) return false;
  return accepted.some((answer) => {
    const other = asNumber(answer);
    // The bank rounds to four places, so compare no finer than that.
    return other !== null && Math.abs(other - value) < 5e-5;
  });
}

export function statusOf(question, userAnswer) {
  if (!isAnswered(userAnswer)) return AnswerStatus.OMITTED;
  return matchesAnswer(question, userAnswer) ? AnswerStatus.CORRECT : AnswerStatus.INCORRECT;
}

/**
 * Options arrive as `"A) 12"`; split them into the letter and the body so the
 * UI can style them separately.
 */
export function splitOption(option) {
  const text = String(option ?? '');
  return { letter: text.slice(0, 1), body: text.slice(3) };
}

/** Full option text for a letter, falling back to the letter itself. */
export function optionTextFor(question, letter) {
  const normalised = normaliseAnswer(letter);
  if (!normalised) return '';
  if (question.type !== QuestionType.MULTIPLE_CHOICE || !Array.isArray(question.options)) {
    return normalised;
  }
  const match = question.options.find(
    (option) => splitOption(option).letter.toUpperCase() === normalised,
  );
  return match ?? normalised;
}

export function difficultyModifier(question) {
  return String(question.difficulty ?? 'Medium').toLowerCase();
}
