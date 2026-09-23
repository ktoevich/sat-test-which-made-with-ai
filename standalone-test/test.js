/**
 * A digital SAT Math test that runs straight from disk: open index.html and
 * module 1 begins. No account, no server.
 *
 * Two modules of 22 questions, 35 minutes each. Module 2 is the harder one
 * when module 1 went well (15 of 22 right, the pass mark the main app uses).
 * The attempt is kept in localStorage, so a reload carries on where it was —
 * the clock keeps running, as it would on test day.
 */
(function () {
  'use strict';

  const TESTS = window.SAT_TESTS || [];
  const MODULE_MINUTES = 35;
  const PASS_MARK = { correct: 15, outOf: 22 };
  const LOW_TIME_MS = 5 * 60 * 1000;
  const ATTEMPT_KEY = 'sat-standalone:attempt';
  const NEXT_KEY = 'sat-standalone:next-test';
  const HISTORY_KEY = 'sat-standalone:history';
  const TIMER_KEY = 'sat-standalone:timer-hidden';
  // The demo key Desmos publishes for development, as the main app uses.
  const DESMOS_URL = 'https://www.desmos.com/api/v1.10/calculator.js?apiKey=dcb31709b452b1cf9dc26972add0fda6';

  const $ = (id) => document.getElementById(id);

  // Storage can be missing or throw (private windows, blocked site data); the
  // test still runs, it just will not survive a reload.
  const store = {
    get(key) {
      try { return JSON.parse(localStorage.getItem(key)); } catch (error) { return null; }
    },
    set(key, value) {
      try { localStorage.setItem(key, JSON.stringify(value)); } catch (error) { /* ignore */ }
    },
  };

  let attempt = null;
  let ticker = null;

  // --- questions and answers ---------------------------------------------

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, (char) => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]
    ));
  }

  /** Line breaks are paragraphs — except inside a table's indented markup. */
  function formatParagraphs(text) {
    const tables = [];
    const held = String(text ?? '').trim().replace(/<table\b[\s\S]*?<\/table>/gi, (table) => {
      tables.push(table.replace(/>\s+</g, '><'));
      return `\u0000${tables.length - 1}\u0000`;
    });
    return held
      .replace(/\s*(\u0000\d+\u0000)\s*/g, '$1')
      .replace(/\n/g, '<br><br>')
      .replace(/\u0000(\d+)\u0000/g, (_, index) => tables[Number(index)]);
  }

  /** College Board's figures are sized in points; give them pixels and a viewBox. */
  function normaliseFigure(markup) {
    const root = /<svg\b[^>]*>/i.exec(markup || '');
    if (!root) return markup || '';
    const tag = root[0];
    const read = (name) => {
      const match = new RegExp(`\\s${name}\\s*=\\s*"([^"]*)"`, 'i').exec(tag);
      return match ? match[1] : null;
    };
    const units = { '': 1, px: 1, pt: 96 / 72, pc: 16, in: 96, cm: 96 / 2.54, mm: 96 / 25.4 };
    const pixels = (length) => {
      const match = /^\s*([\d.]+)\s*([a-z]*)\s*$/i.exec(length || '');
      const value = match ? Number(match[1]) * (units[match[2].toLowerCase()] ?? NaN) : NaN;
      return value > 0 ? value : null;
    };
    const box = (read('viewBox') || '').trim().split(/[\s,]+/).map(Number);
    const hasBox = box.length === 4 && box.every(Number.isFinite) && box[2] > 0 && box[3] > 0;
    let width = pixels(read('width'));
    let height = pixels(read('height'));
    if (!(width && height)) {
      if (!hasBox) return markup;
      [, , width, height] = box;
    }
    let attributes = ` width="${Math.round(width)}" height="${Math.round(height)}"`;
    if (!hasBox) attributes += ` viewBox="0 0 ${width} ${height}"`;
    const sized = tag.replace(/\s(width|height)\s*=\s*"[^"]*"/gi, '').replace(/(\/?>)$/, `${attributes}$1`);
    return markup.slice(0, root.index) + sized + markup.slice(root.index + tag.length);
  }

  const normalise = (answer) => (answer == null ? '' : String(answer).trim().toUpperCase());

  function asNumber(answer) {
    const text = normalise(answer).replace(/\s+/g, '').replace(/,/g, '');
    if (/^-?(?:\d+\.?\d*|\.\d+)$/.test(text)) return Number(text);
    const fraction = /^(-?\d+)\/(\d+)$/.exec(text);
    if (fraction && Number(fraction[2]) !== 0) return Number(fraction[1]) / Number(fraction[2]);
    return null;
  }

  function isCorrect(question, given) {
    const answer = normalise(given);
    if (!answer) return false;
    const accepted = [question.answer, ...(question.accepted_answers || [])].map(normalise).filter(Boolean);
    if (accepted.includes(answer)) return true;
    const value = asNumber(answer);
    if (value === null) return false;
    // The bank rounds grid-in answers to four places; compare no finer.
    return accepted.some((other) => asNumber(other) !== null && Math.abs(asNumber(other) - value) < 5e-5);
  }

  function splitOption(option) {
    const text = String(option ?? '');
    return { letter: text.slice(0, 1), body: text.slice(3) };
  }

  function renderMath(root) {
    if (typeof window.renderMathInElement !== 'function') return;
    window.renderMathInElement(root, {
      delimiters: [{ left: '$', right: '$', display: false }],
      throwOnError: false,
    });
  }

  /** Map a raw score onto 200-800, to the nearest 10 — the main app's formula. */
  function scaledScore(correct, total) {
    if (!total || correct <= 0) return 200;
    if (correct >= total) return 800;
    return Math.round((200 + (correct / total) * 600) / 10) * 10;
  }

  // --- the attempt --------------------------------------------------------

  const test = () => TESTS[attempt.test];
  const moduleQuestions = (number = attempt.module) => (
    number === 1 ? test().module_1 : test()[`module_2_${attempt.level}`]
  );
  const slot = (number = attempt.module) => number - 1;
  const answerAt = (index, number = attempt.module) => attempt.answers[slot(number)][index] ?? '';
  const save = () => store.set(ATTEMPT_KEY, attempt);

  function correctIn(number) {
    return moduleQuestions(number).reduce(
      (total, question, index) => total + (isCorrect(question, answerAt(index, number)) ? 1 : 0), 0,
    );
  }

  function startTest(index) {
    attempt = {
      test: ((index % TESTS.length) + TESTS.length) % TESTS.length,
      module: 1,
      level: null,
      stage: 'exam',
      index: 0,
      answers: [[], []],
      marked: [[], []],
      struck: [{}, {}],
      deadline: Date.now() + MODULE_MINUTES * 60 * 1000,
    };
    store.set(NEXT_KEY, attempt.test + 1);
    save();
    render();
  }

  function finishModule() {
    closePopups();
    if (attempt.module === 1) {
      const needed = Math.ceil((moduleQuestions(1).length * PASS_MARK.correct) / PASS_MARK.outOf);
      attempt.level = correctIn(1) >= needed ? 'HIGHER' : 'LOWER';
      attempt.stage = 'break';
    } else {
      attempt.stage = 'results';
      recordHistory();
    }
    attempt.deadline = null;
    save();
    render();
  }

  function startModule2() {
    attempt.module = 2;
    attempt.stage = 'exam';
    attempt.index = 0;
    attempt.deadline = Date.now() + MODULE_MINUTES * 60 * 1000;
    save();
    render();
  }

  function recordHistory() {
    const correct = correctIn(1) + correctIn(2);
    const total = moduleQuestions(1).length + moduleQuestions(2).length;
    const history = store.get(HISTORY_KEY) || [];
    history.push({ test: test().id, score: scaledScore(correct, total), correct, total, at: Date.now() });
    store.set(HISTORY_KEY, history.slice(-50));
  }

  function goTo(index) {
    attempt.stage = 'exam';
    attempt.index = Math.max(0, Math.min(index, moduleQuestions().length - 1));
    save();
    closePopups();
    render();
  }

  // --- rendering ----------------------------------------------------------

  function render() {
    const stage = attempt.stage;
    $('screen-exam').hidden = stage !== 'exam';
    $('screen-review').hidden = stage !== 'review';
    $('screen-break').hidden = stage !== 'break';
    $('screen-results').hidden = stage !== 'results';
    $('foot').hidden = stage === 'results';
    const running = stage === 'exam' || stage === 'review';
    $('timer-box').hidden = !running;
    $('tools').style.visibility = running ? 'visible' : 'hidden';
    if (!running) closePopups();

    $('module-title').textContent = stage === 'results'
      ? 'Math: Results'
      : `Math: Module ${attempt.module}`;
    $('test-name').textContent = `Practice test ${attempt.test + 1} of ${TESTS.length}`;

    if (stage === 'exam') renderQuestion();
    if (stage === 'review') renderReview();
    if (stage === 'break') renderBreak();
    if (stage === 'results') renderResults();
    renderFooter();
    tick();
  }

  function renderQuestion() {
    const questions = moduleQuestions();
    const index = attempt.index;
    const question = questions[index];

    const figure = question.image ? normaliseFigure(question.image) : '';
    $('figure').innerHTML = figure;
    $('figure').hidden = !figure;
    $('question-text').innerHTML = formatParagraphs(question.text);
    $('qnum').textContent = String(index + 1);
    $('mark-btn').classList.toggle('is-on', attempt.marked[slot()].includes(index));

    const answers = $('answers');
    answers.innerHTML = '';
    if (question.type === 'SPR') renderGridIn(answers, index);
    else renderChoices(answers, question, index);

    renderMath($('question-text'));
    renderMath(answers);
    $('screen-exam').querySelectorAll('.pane').forEach((pane) => { pane.scrollTop = 0; });
  }

  function renderChoices(host, question, index) {
    const selected = answerAt(index);
    const struck = attempt.struck[slot()][index] || [];

    (question.options || []).forEach((option) => {
      const { letter, body } = splitOption(option);
      const row = document.createElement('div');
      row.className = 'choice';
      row.classList.toggle('is-selected', selected === letter);
      row.classList.toggle('is-struck', struck.includes(letter));
      row.innerHTML = `
        <button type="button" class="choice__main">
          <span class="choice__letter">${escapeHtml(letter)}</span>
          <span class="choice__body">${body}</span>
        </button>
        <button type="button" class="choice__strike" title="${struck.includes(letter) ? 'Undo' : 'Cross out'} ${escapeHtml(letter)}">${struck.includes(letter) ? 'Undo' : escapeHtml(letter)}</button>`;

      row.querySelector('.choice__main').addEventListener('click', () => {
        const list = attempt.struck[slot()][index] || [];
        attempt.struck[slot()][index] = list.filter((item) => item !== letter);
        attempt.answers[slot()][index] = letter;
        save();
        renderQuestion();
        renderFooter();
      });
      row.querySelector('.choice__strike').addEventListener('click', () => {
        const list = attempt.struck[slot()][index] || [];
        if (list.includes(letter)) {
          attempt.struck[slot()][index] = list.filter((item) => item !== letter);
        } else {
          attempt.struck[slot()][index] = [...list, letter];
          // Crossing out the chosen answer takes the choice back.
          if (answerAt(index) === letter) attempt.answers[slot()][index] = '';
        }
        save();
        renderQuestion();
      });
      host.append(row);
    });
  }

  function renderGridIn(host, index) {
    host.innerHTML = `
      <input class="spr__field" id="spr-field" type="text" inputmode="decimal" autocomplete="off"
             maxlength="6" aria-label="Your answer">
      <div class="spr__preview">Answer Preview: <span id="spr-preview"></span></div>
      <ul class="spr__rules">
        <li>If you find more than one correct answer, enter only one.</li>
        <li>You can enter up to 5 characters for a positive answer and up to 6 for a negative one.</li>
        <li>If your answer is a fraction that doesn't fit, enter the decimal equivalent.</li>
        <li>If your answer is a decimal that doesn't fit, round or truncate it at the fourth digit.</li>
        <li>If your answer is a mixed number (such as 3½), enter it as an improper fraction (7/2) or its decimal equivalent (3.5).</li>
        <li>Don't enter symbols such as a percent sign, comma, or dollar sign.</li>
      </ul>`;
    const field = host.querySelector('#spr-field');
    const preview = host.querySelector('#spr-preview');
    const showPreview = () => {
      const value = field.value.trim();
      const fraction = /^(-?)(\d+)\/(\d+)$/.exec(value);
      preview.textContent = fraction ? `$${fraction[1]}\\frac{${fraction[2]}}{${fraction[3]}}$` : value;
      renderMath(preview);
    };
    field.value = answerAt(index);
    showPreview();
    field.addEventListener('input', () => {
      field.value = field.value.replace(/[^0-9./-]/g, '');
      attempt.answers[slot()][index] = field.value.trim();
      save();
      showPreview();
      renderFooter();
    });
  }

  function gridHtml(currentIndex) {
    const marked = attempt.marked[slot()];
    return moduleQuestions().map((_, index) => {
      const classes = ['cell'];
      if (answerAt(index)) classes.push('is-answered');
      if (marked.includes(index)) classes.push('is-flagged');
      if (index === currentIndex) classes.push('is-current');
      return `<button type="button" class="${classes.join(' ')}" data-index="${index}">${index + 1}</button>`;
    }).join('');
  }

  function bindGrid(host) {
    host.querySelectorAll('.cell').forEach((cell) => {
      cell.addEventListener('click', () => goTo(Number(cell.dataset.index)));
    });
  }

  function renderReview() {
    $('review-module').textContent = `Math: Module ${attempt.module} Questions`;
    $('review-grid').innerHTML = gridHtml(-1);
    bindGrid($('review-grid'));
  }

  function renderBreak() {
    $('break-text').textContent = `Module 2 has ${moduleQuestions(2).length} questions and ${MODULE_MINUTES} minutes. `
      + 'The clock starts when you press the button.';
  }

  function renderFooter() {
    const total = moduleQuestions().length;
    const inExam = attempt.stage === 'exam';
    $('map-btn').hidden = !inExam;
    $('map-btn').firstChild.textContent = `Question ${attempt.index + 1} of ${total} `;
    $('back-btn').hidden = attempt.stage === 'break';
    $('next-btn').hidden = attempt.stage === 'break';
    $('back-btn').disabled = inExam && attempt.index === 0;
    $('next-btn').textContent = attempt.stage === 'review' && attempt.module === 2 ? 'Submit' : 'Next';
    if (!$('map').hidden) {
      $('map-title').textContent = `Math: Module ${attempt.module} Questions`;
      $('map-grid').innerHTML = gridHtml(attempt.index);
      bindGrid($('map-grid'));
    }
  }

  function renderResults() {
    const counts = [1, 2].map((number) => ({
      correct: correctIn(number),
      total: moduleQuestions(number).length,
    }));
    const correct = counts[0].correct + counts[1].correct;
    const total = counts[0].total + counts[1].total;
    $('score').textContent = String(scaledScore(correct, total));
    $('stats').innerHTML = `
      <div class="stat"><b>${correct} / ${total}</b><span>correct</span></div>
      <div class="stat"><b>${counts[0].correct} / ${counts[0].total}</b><span>Module 1</span></div>
      <div class="stat"><b>${counts[1].correct} / ${counts[1].total}</b><span>Module 2 · ${attempt.level === 'HIGHER' ? 'harder' : 'easier'}</span></div>`;

    $('test-select').innerHTML = TESTS.map((_, index) => (
      `<option value="${index}"${index === attempt.test ? ' selected' : ''}>Practice test ${index + 1}</option>`
    )).join('');

    const history = (store.get(HISTORY_KEY) || []).slice(-6).reverse();
    $('history').innerHTML = history.length > 1
      ? `<p class="history">Recent scores: ${history.map((item) => `<b>${item.score}</b>`).join(' · ')}</p>`
      : '';

    const list = $('answer-list');
    list.innerHTML = '';
    [1, 2].forEach((number) => {
      const heading = document.createElement('h3');
      heading.textContent = `Module ${number}`;
      list.append(heading);
      moduleQuestions(number).forEach((question, index) => list.append(reviewItem(question, index, number)));
    });
  }

  function reviewItem(question, index, number) {
    const given = answerAt(index, number);
    const right = isCorrect(question, given);
    const item = document.createElement('details');
    item.className = `review-item ${right ? 'is-right' : 'is-wrong'}`;
    const key = question.type === 'SPR'
      ? [question.answer, ...(question.accepted_answers || [])].join(' or ')
      : question.answer;
    item.innerHTML = `
      <summary>
        <span class="review-item__num">${index + 1}</span>
        <span class="review-item__meta">${escapeHtml(question.domain || '')} · ${escapeHtml(question.difficulty || '')}
          — your answer: <b>${escapeHtml(given || 'omitted')}</b>, correct: <b>${escapeHtml(key)}</b></span>
        <span class="review-item__verdict">${right ? '✓' : given ? '✗' : '—'}</span>
      </summary>`;

    // The body is built only when opened: 44 questions of figures and
    // formulas at once would make the results page slow to appear.
    item.addEventListener('toggle', () => {
      if (!item.open || item.querySelector('.review-item__body')) return;
      const body = document.createElement('div');
      body.className = 'review-item__body';
      const figure = question.image ? `<div class="figure">${normaliseFigure(question.image)}</div>` : '';
      const options = question.type === 'SPR' ? '' : `<ul class="review-item__options">${
        (question.options || []).map((option) => {
          const { letter, body: text } = splitOption(option);
          const classes = [letter === question.answer ? 'is-key' : '', letter === given ? 'is-mine' : ''].join(' ');
          return `<li class="${classes}"><b>${escapeHtml(letter)})</b> ${text}</li>`;
        }).join('')}</ul>`;
      const rationale = question.rationale
        ? `<div class="review-item__rationale"><b>Explanation</b><br>${formatParagraphs(question.rationale)}</div>`
        : '';
      body.innerHTML = `${figure}<div class="question-text">${formatParagraphs(question.text)}</div>${options}${rationale}`;
      item.append(body);
      renderMath(body);
    });
    return item;
  }

  // --- the clock ----------------------------------------------------------

  function tick() {
    if (!attempt || !attempt.deadline || (attempt.stage !== 'exam' && attempt.stage !== 'review')) return;
    const left = attempt.deadline - Date.now();
    if (left <= 0) {
      finishModule();
      return;
    }
    const seconds = Math.ceil(left / 1000);
    const clock = $('timer');
    clock.textContent = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
    clock.classList.toggle('is-low', left <= LOW_TIME_MS);
    // The last five minutes are always shown, as on test day.
    clock.classList.toggle('is-hidden', Boolean(store.get(TIMER_KEY)) && left > LOW_TIME_MS);
    $('timer-toggle').textContent = store.get(TIMER_KEY) ? 'Show' : 'Hide';
  }

  // --- tools ---------------------------------------------------------------

  function closePopups() {
    $('map').hidden = true;
    $('ref').hidden = true;
  }

  let desmos = null;
  let desmosLoading = false;

  function toggleCalculator() {
    const panel = $('calc');
    panel.hidden = !panel.hidden;
    $('calc-btn').classList.toggle('is-on', !panel.hidden);
    if (panel.hidden || desmos || desmosLoading) return;

    const mount = () => {
      $('calc-notice').remove();
      desmos = window.Desmos.GraphingCalculator($('calc-host'), { settingsMenu: false, keypad: true });
    };
    if (window.Desmos) { mount(); return; }
    desmosLoading = true;
    const script = document.createElement('script');
    script.src = DESMOS_URL;
    script.onload = () => { desmosLoading = false; if (window.Desmos) mount(); };
    script.onerror = () => {
      desmosLoading = false;
      script.remove();
      $('calc-notice').textContent = 'The calculator needs an internet connection. Close it and try again once you are online.';
    };
    document.head.append(script);
  }

  function makeDraggable(panel, handle) {
    let start = null;
    handle.addEventListener('pointerdown', (event) => {
      if (event.target.closest('button')) return;
      const rect = panel.getBoundingClientRect();
      start = { x: event.clientX - rect.left, y: event.clientY - rect.top };
      handle.setPointerCapture(event.pointerId);
    });
    handle.addEventListener('pointermove', (event) => {
      if (!start) return;
      const maxX = window.innerWidth - 60;
      const maxY = window.innerHeight - 40;
      panel.style.left = `${Math.min(maxX, Math.max(0, event.clientX - start.x))}px`;
      panel.style.top = `${Math.min(maxY, Math.max(0, event.clientY - start.y))}px`;
    });
    handle.addEventListener('pointerup', () => { start = null; });
  }

  // --- wiring --------------------------------------------------------------

  function bind() {
    $('back-btn').addEventListener('click', () => {
      if (attempt.stage === 'review') goTo(moduleQuestions().length - 1);
      else if (attempt.index > 0) goTo(attempt.index - 1);
    });
    $('next-btn').addEventListener('click', () => {
      if (attempt.stage === 'exam') {
        if (attempt.index < moduleQuestions().length - 1) {
          goTo(attempt.index + 1);
        } else {
          attempt.stage = 'review';
          save();
          closePopups();
          render();
        }
      } else if (attempt.stage === 'review') {
        const open = moduleQuestions().filter((_, index) => !answerAt(index)).length;
        const warning = attempt.module === 1
          ? `Move on to Module 2? You can't come back to Module 1.${open ? ` ${open} question(s) are unanswered.` : ''}`
          : `Submit the test?${open ? ` ${open} question(s) are unanswered.` : ''}`;
        if (window.confirm(warning)) finishModule();
      }
    });
    $('mark-btn').addEventListener('click', () => {
      const marked = attempt.marked[slot()];
      const at = marked.indexOf(attempt.index);
      if (at >= 0) marked.splice(at, 1); else marked.push(attempt.index);
      save();
      $('mark-btn').classList.toggle('is-on', at < 0);
      renderFooter();
    });
    $('map-btn').addEventListener('click', () => {
      $('map').hidden = !$('map').hidden;
      renderFooter();
    });
    $('map-close').addEventListener('click', () => { $('map').hidden = true; });
    $('map-review').addEventListener('click', () => {
      attempt.stage = 'review';
      save();
      closePopups();
      render();
    });
    $('start-module-2').addEventListener('click', startModule2);
    $('timer-toggle').addEventListener('click', () => {
      store.set(TIMER_KEY, !store.get(TIMER_KEY));
      tick();
    });
    $('calc-btn').addEventListener('click', toggleCalculator);
    $('calc-close').addEventListener('click', toggleCalculator);
    makeDraggable($('calc'), $('calc-head'));
    $('ref-btn').addEventListener('click', () => {
      $('ref').hidden = false;
      renderMath($('ref-body'));
    });
    $('ref-close').addEventListener('click', () => { $('ref').hidden = true; });
    $('ref').addEventListener('click', (event) => { if (event.target === $('ref')) $('ref').hidden = true; });

    $('next-test-btn').addEventListener('click', () => startTest(attempt.test + 1));
    $('retake-btn').addEventListener('click', () => startTest(attempt.test));
    $('test-select').addEventListener('change', (event) => {
      if (window.confirm(`Start practice test ${Number(event.target.value) + 1}?`)) startTest(Number(event.target.value));
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') closePopups();
      if (attempt.stage !== 'exam' || event.target.closest('input, select, textarea')) return;
      if (event.key === 'ArrowRight') $('next-btn').click();
      if (event.key === 'ArrowLeft' && attempt.index > 0) $('back-btn').click();
    });
  }

  function restore() {
    const saved = store.get(ATTEMPT_KEY);
    if (!saved || saved.stage === 'results' || !TESTS[saved.test]) return null;
    // A saved attempt from an older build of the tests may not fit any more.
    if (saved.level && !TESTS[saved.test][`module_2_${saved.level}`]) return null;
    return saved;
  }

  function init() {
    if (!TESTS.length) {
      $('fatal').hidden = false;
      return;
    }
    bind();
    attempt = restore();
    if (attempt) {
      render();
    } else {
      // ?test=3 opens a given test; otherwise each visit takes the next one.
      const asked = Number(new URLSearchParams(window.location.search).get('test'));
      startTest(asked >= 1 ? asked - 1 : Number(store.get(NEXT_KEY)) || 0);
    }
    ticker = window.setInterval(tick, 500);
  }

  // KaTeX and the tests are deferred scripts too; they have run by now.
  init();
}());
