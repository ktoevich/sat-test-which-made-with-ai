/** Question fixtures shaped like the payloads the API returns. */

export const multipleChoice = (id, difficulty, answer) => ({
  question_id: id,
  type: 'MCQ',
  difficulty,
  text: `Prompt ${id}`,
  options: ['A) one', 'B) two', 'C) three', 'D) four'],
  answer,
  rationale: 'Because the two expressions are equal.',
  skill: 'Algebra',
  image: null,
});

export const gridIn = (id) => ({
  question_id: id,
  type: 'SPR',
  difficulty: 'Medium',
  text: `Grid-in ${id}`,
  answer: '42',
  image: { xEnd: 4, yEnd: 4, step: 2, draw: '<circle r="1"/>' },
});

export const MODULE_1 = [
  multipleChoice('m1a', 'Easy', 'A'),
  multipleChoice('m1b', 'Hard', 'C'),
  gridIn('m1c'),
];

export const MODULE_2 = [multipleChoice('m2a', 'Easy', 'B'), gridIn('m2b')];
