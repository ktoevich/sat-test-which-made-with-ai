/** Owns which of the top-level screens is visible. */

import { byId, setVisible } from '../core/dom.js';

export const Screen = {
  AUTH: 'auth',
  LOBBY: 'lobby',
  EXAM: 'exam',
};

const elements = {
  auth: () => byId('auth-screen'),
  lobby: () => byId('lobby-screen'),
  exam: () => byId('exam-screen'),
  examFooter: () => byId('exam-footer'),
  topBar: () => byId('top-bar'),
  sectionInfo: () => byId('section-info'),
  timer: () => byId('timer'),
};

export function showScreen(screen) {
  const isExam = screen === Screen.EXAM;

  setVisible(elements.auth(), screen === Screen.AUTH);
  setVisible(elements.lobby(), screen === Screen.LOBBY);
  setVisible(elements.exam(), isExam);
  setVisible(elements.examFooter(), isExam);
  setVisible(elements.topBar(), isExam);
  setVisible(elements.sectionInfo(), isExam);
  setVisible(elements.timer(), isExam);
}
