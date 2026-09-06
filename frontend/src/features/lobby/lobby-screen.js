/** Dashboard: aggregate stats plus the list of past attempts, loaded from the API. */

import { listAttempts } from '../../api/attempts-api.js';
import { ApiError } from '../../api/client.js';
import { byId, clear, el, setText } from '../../core/dom.js';

const DATE_OPTIONS = {
  year: 'numeric',
  month: 'short',
  day: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
};

/** Attempt timestamps come back as UTC ISO strings. */
function formatDate(isoString) {
  const date = new Date(isoString);
  return Number.isNaN(date.getTime()) ? String(isoString) : date.toLocaleString(undefined, DATE_OPTIONS);
}

export class LobbyScreen {
  /**
   * @param {{ onStartTest: () => void,
   *           onLogout: () => void,
   *           onViewAttempt: (attempt: object) => void }} handlers
   */
  constructor({ onStartTest, onLogout, onViewAttempt }) {
    this.onViewAttempt = onViewAttempt;
    this.elements = {
      username: byId('lobby-username'),
      testsTaken: byId('stat-tests'),
      bestScore: byId('stat-best'),
      averageScore: byId('stat-average'),
      historyBody: byId('history-table-body'),
      noticeSlot: byId('lobby-notice-slot'),
    };

    byId('start-test-btn').addEventListener('click', onStartTest);
    byId('logout-btn').addEventListener('click', onLogout);
  }

  /**
   * Draw the dashboard for a user and load their history.
   * @param {{ username: string }} user
   */
  async render(user) {
    setText(this.elements.username, user.username);
    this.#renderPlaceholder('Loading your history...');

    try {
      const { attempts, summary } = await listAttempts();
      setText(this.elements.testsTaken, summary.taken);
      setText(this.elements.bestScore, summary.best ?? '-');
      setText(this.elements.averageScore, summary.average ?? '-');
      this.#renderHistory(attempts);
    } catch (error) {
      if (error instanceof ApiError && error.isUnauthenticated) throw error;
      this.#renderPlaceholder('Could not load your history.');
      this.showNotice(
        error instanceof ApiError ? error.message : 'Could not load your test history.',
      );
    }
  }

  /** Show a message above the dashboard, e.g. "no tests available". */
  showNotice(message) {
    clear(this.elements.noticeSlot);
    if (message) {
      this.elements.noticeSlot.append(
        el('div', { className: 'notice notice--warning', text: message }),
      );
    }
  }

  clearNotice() {
    this.showNotice('');
  }

  #renderPlaceholder(message) {
    clear(this.elements.historyBody);
    this.elements.historyBody.append(
      el('tr', {}, [el('td', { className: 'data-table__empty', colspan: '4', text: message })]),
    );
  }

  #renderHistory(attempts) {
    if (attempts.length === 0) {
      this.#renderPlaceholder("You haven't taken any tests yet. It's time to start!");
      return;
    }

    const body = this.elements.historyBody;
    clear(body);

    // The API already returns them newest first.
    attempts.forEach((attempt) => {
      const viewButton = el('button', {
        type: 'button',
        className: 'btn-view',
        text: 'Details',
      });
      viewButton.addEventListener('click', () => this.onViewAttempt(attempt));

      body.append(
        el('tr', {}, [
          el('td', { text: formatDate(attempt.taken_at) }),
          el('td', { text: attempt.score }),
          el('td', { text: `${attempt.correct}/${attempt.total}` }),
          el('td', {}, [viewButton]),
        ]),
      );
    });
  }
}
