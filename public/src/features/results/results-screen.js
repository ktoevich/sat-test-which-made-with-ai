/** End-of-test screen: scaled score, per-question breakdown, saved history. */

import { saveAttempt } from '../../api/attempts-api.js';
import { ApiError } from '../../api/client.js';
import { byId, clear, el, setHtml, setText, setVisible, show } from '../../core/dom.js';
import { toScaledScore } from '../../core/scoring.js';
import { difficultyTag, statusBadge } from './answer-summary.js';
import { renderScoreBubble } from './score-bubble.js';
import { openSolution } from './solution-modal.js';

export class ResultsScreen {
  /** @param {{ onReturnToLobby: () => void }} handlers */
  constructor({ onReturnToLobby }) {
    this.elements = {
      screen: byId('intermission-screen'),
      title: byId('intermission-title'),
      message: byId('intermission-message'),
      card: byId('final-results'),
      scoreValue: byId('score-value'),
      scoreFill: byId('score-fill'),
      details: byId('score-details'),
      tableBody: byId('review-table-body'),
      saveNotice: byId('results-save-notice'),
    };

    byId('back-to-lobby-btn').addEventListener('click', onReturnToLobby);
  }

  hide() {
    setVisible(this.elements.screen, false);
    setVisible(this.elements.card, false);
  }

  /**
   * Render the results of a finished attempt and store it in the user's history.
   *
   * The score is shown straight away; saving happens in the background so a
   * network hiccup never hides the result the student just earned.
   * @param {import('../exam/exam-state.js').ExamSession} session
   */
  show(session) {
    const { correct, total } = session.totals;
    const score = toScaledScore(correct, total);

    setText(this.elements.title, 'Test Complete!');
    setText(this.elements.message, 'Here is your detailed performance summary.');
    renderScoreBubble(
      { valueEl: this.elements.scoreValue, fillEl: this.elements.scoreFill },
      score,
    );
    setHtml(this.elements.details, ResultsScreen.#summaryHtml(session, correct, total));
    this.#renderBreakdown(session.review);

    show(this.elements.card);
    show(this.elements.screen);

    this.#save({ score, correct, total, details: session.review });
  }

  async #save(attempt) {
    setVisible(this.elements.saveNotice, false);
    try {
      await saveAttempt(attempt);
    } catch (error) {
      setText(
        this.elements.saveNotice,
        error instanceof ApiError
          ? `This attempt was not saved: ${error.message}`
          : 'This attempt was not saved.',
      );
      setVisible(this.elements.saveNotice, true);
    }
  }

  #renderBreakdown(review) {
    const body = this.elements.tableBody;
    clear(body);

    let printedModule = null;
    review.forEach((entry, index) => {
      if (printedModule !== entry.module) {
        printedModule = entry.module;
        body.append(ResultsScreen.#moduleSeparatorRow(entry.module));
      }

      const viewButton = el('button', {
        type: 'button',
        className: 'btn-view',
        text: 'View Solution',
      });
      viewButton.addEventListener('click', () => openSolution(review[index]));

      body.append(
        el('tr', {}, [
          el('td', { text: entry.number }),
          el('td', {}, [difficultyTag(entry.question)]),
          el('td', {}, [statusBadge(entry)]),
          el('td', {}, [viewButton]),
        ]),
      );
    });
  }

  static #moduleSeparatorRow(moduleNumber) {
    const separator = el('div', {
      className: 'module-separator',
      text: `Module ${moduleNumber}`,
    });
    const cell = el('td', { colspan: '4', style: 'padding: 0; background: none;' }, [separator]);
    return el('tr', {}, [cell]);
  }

  static #summaryHtml(session, correct, total) {
    const perModule = Object.entries(session.moduleScores)
      .map(([number, score]) => `Module ${number}: ${score.correct}/${score.total}`)
      .join(' | ');
    return `<strong>Raw Score:</strong> ${correct} / ${total} correct<br><span>(${perModule})</span>`;
  }
}
