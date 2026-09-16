/**
 * The lobby: the student's profile, the tests, their history, and the
 * community in the sidebar. The same profile card shows another student in
 * observer mode, reached from the leaderboard or a search, with actions to
 * befriend or message them instead of the settings.
 */

import { listAttempts } from '../../api/attempts-api.js';
import { ApiError } from '../../api/client.js';
import {
  fetchLeaderboard,
  fetchPlatformStats,
  fetchPublicProfile,
  searchUsers,
} from '../../api/community-api.js';
import { acceptFriendRequest, fetchFriends, sendFriendRequest } from '../../api/social-api.js';
import { SECTIONS, sectionOf } from '../../config.js';
import { byId, clear, el, setText, setVisible } from '../../core/dom.js';
import { formatDuration, sectionName, t } from '../../core/i18n.js';
import { domainColor, ratingSummary, renderRatingChart, renderTopicsChart } from './charts.js';

const DATE_OPTIONS = { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' };

/** Attempt timestamps come back as UTC ISO strings. */
function formatDate(isoString, options = DATE_OPTIONS) {
  const date = new Date(isoString);
  return Number.isNaN(date.getTime()) ? String(isoString) : date.toLocaleString(undefined, options);
}

const DOMAINS = {
  math: ['Algebra', 'Advanced Math', 'Problem-Solving and Data Analysis', 'Geometry and Trigonometry'],
  reading: ['Craft and Structure', 'Information and Ideas', 'Expression of Ideas', 'Standard English Conventions'],
};

const avatarOf = (user) => user?.avatar || '🎓';

export class LobbyScreen {
  /**
   * @param {{ onStartTest: (section: string, testId?: string) => void,
   *           onLogout: () => void,
   *           onViewAttempt: (attempt: object) => void,
   *           onPractice: (section: string, domain: string) => void,
   *           onOpenFriends: () => void,
   *           onOpenMessages: (userId?: number) => void,
   *           onOpenSettings: () => void }} handlers
   */
  constructor(handlers) {
    this.handlers = handlers;
    this.user = null;
    /** @type {object|null} the student being viewed in observer mode */
    this.observed = null;
    this.topicsMode = 'circle';
    this.leaderboardSection = 'math';
    this.analytics = { rating_points: [], topics: [] };
    this.history = [];

    this.elements = {
      noticeSlot: byId('lobby-notice-slot'),
      observerBanner: byId('observer-banner'),
      observerName: byId('observer-name'),
      avatar: byId('profile-avatar'),
      username: byId('lobby-username'),
      tier: byId('profile-tier'),
      fullName: byId('profile-fullname'),
      location: byId('profile-location'),
      since: byId('profile-since'),
      ownerActions: byId('profile-actions'),
      observerActions: byId('observer-actions'),
      friendButton: byId('observer-friend-btn'),
      rating: byId('profile-rating'),
      maxRating: byId('profile-max-rating'),
      friends: byId('profile-friends'),
      testsTaken: byId('stat-tests'),
      bestMath: byId('stat-best'),
      bestReading: byId('stat-best-reading'),
      average: byId('stat-average'),
      ratingChart: byId('rating-chart'),
      ratingTooltip: byId('rating-tooltip'),
      ratingSummary: byId('rating-summary'),
      topicsChart: byId('topics-chart'),
      topicsMode: byId('topics-mode'),
      testsCard: byId('tests-card'),
      historyTitle: byId('history-title'),
      historyBody: byId('history-table-body'),
      platformStats: byId('platform-stats'),
      countries: byId('platform-countries'),
      leaderboardTabs: byId('leaderboard-tabs'),
      leaderboard: byId('leaderboard-list'),
      search: byId('user-search'),
      searchResults: byId('user-search-results'),
    };

    this.#bindEvents();
  }

  #bindEvents() {
    const { handlers, elements } = this;
    for (const button of [byId('start-test-btn'), byId('start-reading-btn')]) {
      button.addEventListener('click', () => handlers.onStartTest(button.dataset.section));
    }
    byId('open-friends-btn').addEventListener('click', () => handlers.onOpenFriends());
    byId('profile-friends-box').addEventListener('click', () => {
      if (!this.observed) handlers.onOpenFriends();
    });
    byId('open-messages-btn').addEventListener('click', () => handlers.onOpenMessages());
    byId('open-settings-btn').addEventListener('click', () => handlers.onOpenSettings());
    byId('observer-exit').addEventListener('click', () => this.exitObserver());
    byId('observer-message-btn').addEventListener('click', () => {
      if (this.observed) handlers.onOpenMessages(this.observed.user.id);
    });
    elements.friendButton.addEventListener('click', () => this.#befriendObserved());

    elements.topicsMode.querySelectorAll('[data-mode]').forEach((button) => {
      button.addEventListener('click', () => {
        this.topicsMode = button.dataset.mode;
        elements.topicsMode.querySelectorAll('[data-mode]').forEach((b) => b.classList.toggle('is-active', b === button));
        this.#renderTopics();
      });
    });
    elements.leaderboardTabs.querySelectorAll('[data-section]').forEach((button) => {
      button.addEventListener('click', () => {
        this.leaderboardSection = button.dataset.section;
        elements.leaderboardTabs.querySelectorAll('[data-section]').forEach((b) => b.classList.toggle('is-active', b === button));
        this.#loadLeaderboard();
      });
    });

    let searchTimer = null;
    elements.search.addEventListener('input', () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => this.#search(elements.search.value), 180);
    });
    elements.search.addEventListener('focus', () => this.#search(elements.search.value));
    elements.search.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') this.#clearSearch();
      if (event.key === 'Enter') {
        event.preventDefault();
        elements.searchResults.querySelector('.user-row')?.click();
      }
    });
    document.addEventListener('click', (event) => {
      if (!event.target.closest('#user-search, #user-search-results')) clear(elements.searchResults);
    });

    // Practise-a-domain chips under each test card.
    document.querySelectorAll('.topic-chips[data-section]').forEach((holder) => {
      const section = holder.dataset.section;
      DOMAINS[section].forEach((domain) => {
        const chip = el('button', { type: 'button', className: 'topic-chip', text: domain, style: `border-color:${domainColor(domain)}` });
        chip.addEventListener('click', () => handlers.onPractice(section, domain));
        holder.append(chip);
      });
    });

    document.addEventListener('languagechange', () => this.#redrawText());
  }

  // -- your own profile --------------------------------------------------

  /**
   * Draw the dashboard for the signed-in student and load their history.
   * @param {object} user
   */
  async render(user) {
    this.user = user;
    this.observed = null;
    this.#applyMode();
    this.#renderIdentity(user);
    byId('lobby-screen').scrollTo?.({ top: 0 });
    this.#renderPlaceholder(t('lobby_notice_loading'));
    this.#loadSidebar();

    try {
      const { attempts, summary } = await listAttempts();
      this.history = attempts;
      this.#renderSummary(summary, attempts);
      this.#renderHistory(attempts, { own: true });
      const profile = await fetchPublicProfile(user.id);
      this.user = { ...user, ...profile.user };
      this.#renderIdentity(this.user);
      setText(this.elements.friends, profile.friends_count);
      this.analytics = profile.analytics;
      this.#renderCharts();
    } catch (error) {
      if (error instanceof ApiError && error.isUnauthenticated) throw error;
      this.#renderPlaceholder(t('lobby_notice_failed'));
      this.showNotice(error instanceof ApiError ? error.message : t('lobby_notice_failed'));
    }
  }

  /** Reload the profile after something changed: a saved test, a profile edit. */
  refresh() {
    if (this.user && !this.observed) return this.render(this.user);
    return Promise.resolve();
  }

  // -- another student's profile -----------------------------------------

  /** Show another student's profile in the same card, read-only. */
  async viewUser(userId) {
    this.#clearSearch();
    if (this.user && Number(userId) === Number(this.user.id)) {
      this.exitObserver();
      return;
    }
    try {
      const profile = await fetchPublicProfile(userId);
      this.observed = profile;
      this.#applyMode();
      this.#renderIdentity(profile.user);
      setText(this.elements.friends, profile.friends_count);
      this.#renderSummary(profile.summary, profile.history);
      this.history = profile.history;
      this.#renderHistory(profile.history, { own: false });
      this.analytics = profile.analytics;
      this.#renderCharts();
      this.#renderFriendButton(profile.relationship);
      byId('lobby-screen').scrollTo({ top: 0, behavior: 'smooth' });
    } catch (error) {
      this.showNotice(error instanceof ApiError ? error.message : t('lobby_notice_failed'));
    }
  }

  exitObserver() {
    if (!this.observed) return;
    this.observed = null;
    if (this.user) this.render(this.user);
  }

  #applyMode() {
    const observing = Boolean(this.observed);
    setVisible(this.elements.observerBanner, observing);
    setVisible(this.elements.ownerActions, !observing);
    setVisible(this.elements.observerActions, observing);
    setVisible(this.elements.testsCard, !observing);
    this.elements.historyBody.parentElement.parentElement.querySelector('th:last-child').classList.toggle('hidden', observing);
    if (observing) setText(this.elements.observerName, this.observed.user.username);
    setText(
      this.elements.historyTitle,
      observing ? t('history_title_other', { name: this.observed.user.username }) : t('history_title'),
    );
  }

  #renderFriendButton(relationship) {
    const button = this.elements.friendButton;
    const labels = {
      none: 'profile_add_friend',
      outgoing: 'profile_request_sent',
      incoming: 'profile_accept_request',
      friends: 'profile_friends_since',
    };
    setText(button, t(labels[relationship] ?? 'profile_add_friend'));
    button.disabled = relationship === 'outgoing' || relationship === 'friends';
    button.dataset.relationship = relationship;
  }

  async #befriendObserved() {
    if (!this.observed) return;
    try {
      const relationship = this.observed.relationship;
      if (relationship === 'incoming') {
        const overview = await fetchFriends();
        const request = overview.incoming.find((r) => r.user.id === this.observed.user.id);
        if (request) await acceptFriendRequest(request.request_id);
        this.observed.relationship = 'friends';
      } else if (relationship === 'none') {
        const result = await sendFriendRequest(this.observed.user.id);
        this.observed.relationship = result.relationship;
      }
      this.#renderFriendButton(this.observed.relationship);
    } catch (error) {
      this.showNotice(error instanceof ApiError ? error.message : t('lobby_notice_failed'));
    }
  }

  // -- pieces --------------------------------------------------------------

  #renderIdentity(user) {
    const { elements } = this;
    setText(elements.avatar, avatarOf(user));
    setText(elements.username, user.username);
    const tier = user.tier ?? 'Pupil';
    setText(elements.tier, t(`tier_${tier}`));
    elements.tier.className = `tier-badge tier-badge--${tier.split(' ')[0]}`;
    setText(elements.fullName, user.full_name || '');
    setVisible(elements.fullName, Boolean(user.full_name));
    setText(elements.location, user.location ? `📍 ${user.location}` : t('profile_location_unset'));
    setText(
      elements.since,
      user.created_at ? t('profile_since', { date: formatDate(user.created_at, { year: 'numeric', month: 'short' }) }) : '',
    );
    setText(elements.rating, user.rating ?? '-');
    setText(elements.maxRating, user.max_rating ?? '-');
  }

  #renderSummary(summary, attempts) {
    const bySection = summary?.by_section ?? {};
    setText(this.elements.testsTaken, summary?.taken ?? attempts.length);
    setText(this.elements.bestMath, bySection.math?.best ?? '-');
    setText(this.elements.bestReading, bySection.reading?.best ?? '-');
    setText(this.elements.average, summary?.average ?? '-');
  }

  #renderCharts() {
    const points = this.analytics?.rating_points ?? [];
    renderRatingChart(this.elements.ratingChart, this.elements.ratingTooltip, points);
    const summary = ratingSummary(points);
    clear(this.elements.ratingSummary);
    if (summary) {
      const item = (label, value) => el('span', {}, [el('span', { text: `${label} ` }), el('strong', { text: value })]);
      this.elements.ratingSummary.append(
        item(t('chart_tests'), summary.tests),
        item(t('chart_peak'), `${summary.peak} (${formatDate(summary.peakAt, { day: '2-digit', month: '2-digit', year: 'numeric' })})`),
        item(t('chart_best_gain'), `${summary.bestGain >= 0 ? '+' : ''}${summary.bestGain}`),
        item(t('chart_average'), summary.average),
      );
    }
    this.#renderTopics();
  }

  #renderTopics() {
    renderTopicsChart(this.elements.topicsChart, this.analytics?.topics ?? [], this.topicsMode, (section, domain) => {
      if (!this.observed) this.handlers.onPractice(section, domain);
    });
  }

  #renderPlaceholder(message) {
    clear(this.elements.historyBody);
    this.elements.historyBody.append(
      el('tr', {}, [el('td', { className: 'data-table__empty', colspan: '7', text: message })]),
    );
  }

  #renderHistory(attempts, { own }) {
    if (attempts.length === 0) {
      this.#renderPlaceholder(t(own ? 'history_empty' : 'history_empty_other'));
      return;
    }
    const body = this.elements.historyBody;
    clear(body);
    attempts.forEach((attempt) => {
      const delta = attempt.rating_after != null && attempt.rating_before != null ? attempt.rating_after - attempt.rating_before : null;
      const ratingCell = el('td', {}, [
        el('span', { text: attempt.rating_after ?? '—' }),
        delta === null
          ? null
          : el('span', { className: delta >= 0 ? 'rating-delta--up' : 'rating-delta--down', text: ` ${delta >= 0 ? '+' : ''}${delta}` }),
      ]);
      const actions = el('div', { className: 'history-actions' });
      if (own) {
        const details = el('button', { type: 'button', className: 'btn-view', text: t('btn_details') });
        details.addEventListener('click', () => this.handlers.onViewAttempt(attempt));
        actions.append(details);
        if (attempt.test_id) {
          const retake = el('button', { type: 'button', className: 'btn-primary btn--small', text: t('btn_retake') });
          retake.addEventListener('click', () => this.handlers.onStartTest(attempt.section, attempt.test_id));
          actions.append(retake);
        }
      }
      body.append(
        el('tr', {}, [
          el('td', { text: formatDate(attempt.taken_at) }),
          el('td', { text: sectionName(attempt.section) }),
          el('td', {}, [el('strong', { text: attempt.score })]),
          el('td', { text: `${attempt.correct}/${attempt.total}` }),
          el('td', { text: formatDuration(attempt.time_spent) }),
          ratingCell,
          own ? el('td', {}, [actions]) : el('td', { className: 'hidden' }),
        ]),
      );
    });
  }

  #redrawText() {
    const user = this.observed ? this.observed.user : this.user;
    if (user) this.#renderIdentity(user);
    this.#applyMode();
    this.#renderHistory(this.history, { own: !this.observed });
    this.#renderCharts();
    this.#loadSidebar();
  }

  // -- sidebar -------------------------------------------------------------

  async #loadSidebar() {
    this.#loadLeaderboard();
    try {
      const stats = await fetchPlatformStats();
      this.#renderPlatform(stats);
    } catch {
      clear(this.elements.platformStats);
    }
  }

  #renderPlatform(stats) {
    const { platformStats, countries } = this.elements;
    clear(platformStats);
    const metric = (value, label) =>
      el('div', { className: 'platform-metric' }, [
        el('div', { className: 'platform-metric__value', text: value }),
        el('div', { className: 'platform-metric__label', text: label }),
      ]);
    const math = stats.by_section?.math ?? {};
    const reading = stats.by_section?.reading ?? {};
    platformStats.append(
      metric(stats.students, t('side_students')),
      metric(stats.tests_taken, t('side_tests')),
      metric((math.perfect_scorers ?? 0) + (reading.perfect_scorers ?? 0), t('side_perfect')),
      metric(math.average ?? reading.average ?? '-', `${t('side_average')} · ${sectionName(math.average != null ? 'math' : 'reading', { short: true })}`),
    );
    clear(countries);
    if (!stats.countries?.length) {
      countries.append(el('span', { className: 'side-empty', text: t('side_no_countries') }));
      return;
    }
    stats.countries.forEach((country) => {
      countries.append(el('span', { className: 'country-chip', text: `${country.flag} ${country.name} · ${country.students}` }));
    });
  }

  async #loadLeaderboard() {
    const list = this.elements.leaderboard;
    try {
      const { leaderboard } = await fetchLeaderboard(this.leaderboardSection, 10);
      clear(list);
      if (!leaderboard.length) {
        list.append(el('li', { className: 'side-empty', text: t('side_leaderboard_empty') }));
        return;
      }
      leaderboard.forEach((row) => {
        const item = el('li', { className: 'leaderboard__row', title: row.user.username }, [
          el('span', { className: `leaderboard__rank leaderboard__rank--${row.rank}`, text: row.rank <= 3 ? ['🥇', '🥈', '🥉'][row.rank - 1] : `#${row.rank}` }),
          el('span', { className: 'leaderboard__avatar', text: avatarOf(row.user) }),
          el('span', { className: 'leaderboard__who' }, [
            el('span', { className: 'leaderboard__name', text: row.user.username }),
            el('span', { className: 'leaderboard__sub', text: `${row.correct}/${row.total} · ⏱ ${formatDuration(row.time_spent)}` }),
          ]),
          el('span', { className: 'leaderboard__score', text: row.score }),
        ]);
        item.addEventListener('click', () => this.viewUser(row.user.id));
        list.append(item);
      });
    } catch {
      clear(list);
    }
  }

  async #search(query) {
    const results = this.elements.searchResults;
    const text = String(query ?? '').trim();
    try {
      const { users } = await searchUsers(text, 8);
      clear(results);
      if (!users.length) {
        results.append(el('li', { className: 'side-empty', text: t('side_search_empty') }));
        return;
      }
      users.forEach((user) => {
        const row = el('li', { className: 'user-row' }, [
          el('span', { className: 'user-row__avatar', text: avatarOf(user) }),
          el('span', {}, [
            el('div', { className: 'user-row__name', text: user.username }),
            el('div', { className: 'user-row__sub', text: [user.full_name, user.location].filter(Boolean).join(' · ') }),
          ]),
          el('span', { className: 'user-row__rating', text: user.rating }),
        ]);
        row.addEventListener('click', () => this.viewUser(user.id));
        results.append(row);
      });
    } catch {
      clear(results);
    }
  }

  #clearSearch() {
    this.elements.search.value = '';
    clear(this.elements.searchResults);
  }

  /** Show a message above the dashboard, e.g. "no tests available". */
  showNotice(message) {
    clear(this.elements.noticeSlot);
    if (message) {
      this.elements.noticeSlot.append(el('div', { className: 'notice notice--warning', text: message }));
    }
  }

  clearNotice() {
    this.showNotice('');
  }
}

export { SECTIONS, sectionOf };
