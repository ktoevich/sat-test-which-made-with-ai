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

export function statusOf(question, userAnswer) {
  if (!isAnswered(userAnswer)) return AnswerStatus.OMITTED;
  return normaliseAnswer(userAnswer) === normaliseAnswer(question.answer)
    ? AnswerStatus.CORRECT
    : AnswerStatus.INCORRECT;
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
