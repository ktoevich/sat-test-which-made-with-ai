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

const TABLE = /<table\b[\s\S]*?<\/table>/gi;

/**
 * Turn newlines into paragraph breaks for display.
 * A table in the prompt is indented markup: a break inside it is not a
 * paragraph, and the browser would hoist every one of them out above the
 * table — dozens of blank lines that push the question out of sight. The
 * table is a block of its own, so the newline beside it goes too.
 */
export function formatParagraphs(text) {
  const tables = [];
  const held = cleanText(text).replace(TABLE, (table) => {
    tables.push(table.replace(/>\s+</g, '><'));
    return `\u0000${tables.length - 1}\u0000`;
  });
  return held
    .replace(/\s*(\u0000\d+\u0000)\s*/g, '$1')
    // A run of newlines is one paragraph break, however many the bank wrote:
    // taking each of them for a break left a question with four blank lines
    // between what it shows and what it asks.
    .replace(/\n{2,}/g, '<br><br>')
    .replace(/\n/g, '<br>')
    .replace(/\u0000(\d+)\u0000/g, (_, index) => tables[Number(index)]);
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

/** A Reading and Writing question carries the passage it is about. */
export function hasPassage(question) {
  return typeof question?.passage === 'string' && question.passage.trim() !== '';
}
