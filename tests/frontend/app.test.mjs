/**
 * End-to-end walk through the app in jsdom, against an in-memory stand-in for
 * the API: sign up, take both modules, review the results, then sign back in
 * and find the attempt in the history.
 */

import assert from 'node:assert/strict';
import test from 'node:test';

import { COUNTDOWN_WAIT_MS, bootApp, domHelpers, flush, wait } from './helpers/dom.mjs';
import { fakeBackend } from './helpers/fake-backend.mjs';

const PASSWORD = 'sup3rsecret';

test('a full attempt, from sign-up to saved history', async (t) => {
  const backend = fakeBackend();
  const app = await bootApp({ fetchImpl: backend });
  const { byId, isVisible, text, click, type, submit, all } = domHelpers(app.window);

  const submitAuth = async () => {
    submit('auth-form');
    await flush();
  };

  await t.test('a fresh browser lands on the auth screen', () => {
    assert.ok(isVisible('auth-screen'));
    assert.ok(!isVisible('lobby-screen'));
  });

  await t.test('sign-up validates before spending a request', async () => {
    click('auth-tab-register');
    assert.ok(isVisible('auth-username-field'));
    assert.ok(isVisible('auth-confirm-field'));

    byId('auth-email').value = 'Student@Example.com ';
    byId('auth-password').value = PASSWORD;
    byId('auth-confirm').value = 'different';
    await submitAuth();
    assert.match(text('auth-error'), /username/i);

    byId('auth-username').value = 'Nika';
    await submitAuth();
    assert.match(text('auth-error'), /do not match/i);

    byId('auth-password').value = 'short';
    byId('auth-confirm').value = 'short';
    await submitAuth();
    assert.match(text('auth-error'), /at least 8/i);

    assert.ok(
      !app.requests.some((entry) => entry.includes('/api/auth/register')),
      'a locally invalid form should not reach the server',
    );
  });

  await t.test('a valid sign-up opens an empty lobby', async () => {
    byId('auth-password').value = PASSWORD;
    byId('auth-confirm').value = PASSWORD;
    await submitAuth();
    await flush();

    assert.ok(app.requests.includes('POST /api/auth/register'));
    assert.ok(isVisible('lobby-screen'));
    assert.ok(!isVisible('auth-screen'));
    assert.equal(text('lobby-username'), 'Nika');
    assert.equal(text('stat-tests'), '0');
    assert.match(text('history-table-body'), /haven't taken any tests/);
  });

  await t.test('starting a test loads module 1 after the countdown', async () => {
    click('start-test-btn');
    await wait(50);
    assert.ok(app.requests.includes('GET /api/tests/module-1'));

    await wait(COUNTDOWN_WAIT_MS);
    assert.ok(isVisible('exam-screen'));
    assert.ok(isVisible('exam-footer'));
    assert.equal(text('section-info'), 'Math: Module 1');
    assert.equal(text('tracker-btn'), '1 of 3');
    assert.equal(all('.option-item', byId('options-list')).length, 4);
    assert.equal(byId('question-map-grid').children.length, 3);
  });

  await t.test('answering, eliminating and flagging update the navigator', () => {
    click(all('.option-item__content', byId('options-list'))[0]);
    assert.ok(all('.option-item', byId('options-list'))[0].classList.contains('is-selected'));
    assert.ok(byId('question-map-grid').children[0].classList.contains('is-answered'));

    click(all('.option-item__eliminate', byId('options-list'))[1]);
    assert.ok(all('.option-item', byId('options-list'))[1].classList.contains('is-eliminated'));

    click('flag-btn');
    assert.ok(byId('flag-btn').classList.contains('is-flagged'));
    assert.ok(byId('question-map-grid').children[0].classList.contains('is-flagged'));

    assert.equal(byId('prev-btn').disabled, true);
  });

  await t.test('grid-in questions take typed answers without losing focus', () => {
    click('next-btn');
    assert.equal(text('tracker-btn'), '2 of 3');
    click(all('.option-item__content', byId('options-list'))[2]);

    click('next-btn');
    const input = byId('options-list').querySelector('input');
    assert.ok(input, 'expected a text input for the SPR question');
    assert.ok(byId('question-figure').querySelector('svg'), 'expected a rendered coordinate grid');

    type(input, '42');
    assert.equal(byId('options-list').querySelector('input'), input);
    assert.equal(text('next-btn'), 'Finish');
  });

  await t.test('finishing module 1 well requests the harder module 2', async () => {
    click('next-btn');
    assert.ok(isVisible('finish-modal'));

    click('finish-confirm-btn');
    await wait(50);
    assert.ok(app.requests.includes('GET /api/tests/module-2?test_id=t1&target=HIGHER'));

    await wait(COUNTDOWN_WAIT_MS);
    assert.equal(text('section-info'), 'Math: Module 2');
    assert.equal(text('tracker-btn'), '1 of 2');
  });

  await t.test('the results screen scores the attempt and saves it', async () => {
    click(all('.option-item__content', byId('options-list'))[1]);
    click('next-btn');
    click('next-btn');
    click('finish-confirm-btn');
    await flush();

    assert.ok(isVisible('intermission-screen'));
    assert.ok(isVisible('final-results'));
    // 4 of 5 correct -> 200 + 0.8 * 600 = 680.
    assert.equal(text('score-value'), '680');
    assert.equal(all('tr', byId('review-table-body')).length, 7);
    assert.equal(all('.status-badge--correct', byId('review-table-body')).length, 4);
    assert.equal(all('.status-badge--omitted', byId('review-table-body')).length, 1);

    assert.ok(app.requests.includes('POST /api/attempts'));
    assert.ok(!isVisible('results-save-notice'), 'a successful save shows no warning');
  });

  await t.test('the solution modal expands the answer letters', () => {
    click(all('.btn-view', byId('review-table-body'))[0]);
    assert.ok(isVisible('solution-modal'));
    assert.match(text('solution-rationale'), /Because the two expressions/);
    assert.equal(text('solution-correct-answer'), 'A) one');

    click(byId('solution-modal').querySelector('[data-close-modal]'));
    assert.ok(!isVisible('solution-modal'));
  });

  await t.test('returning to the lobby shows the saved attempt', async () => {
    click('back-to-lobby-btn');
    await flush();

    assert.ok(isVisible('lobby-screen'));
    assert.ok(!isVisible('intermission-screen'));
    assert.equal(all('tr', byId('history-table-body')).length, 1);
    assert.equal(text('stat-tests'), '1');
    assert.equal(text('stat-best'), '680');
    assert.equal(text('stat-average'), '680');
  });

  await t.test('the attempt modal lists every question', () => {
    click(byId('history-table-body').querySelector('.btn-view'));
    assert.ok(isVisible('attempt-modal'));
    assert.equal(all('.attempt-question', byId('attempt-questions')).length, 5);
    assert.match(text('attempt-questions'), /Omitted \(No answer\)/);
    assert.match(text('attempt-summary'), /4 \/ 5 correct/);
    click(byId('attempt-modal').querySelector('[data-close-modal]'));
  });

  await t.test('logging out ends the session and resets the form', async () => {
    click('logout-btn');
    await flush();

    assert.ok(app.requests.includes('POST /api/auth/logout'));
    assert.ok(isVisible('auth-screen'));
    assert.ok(!isVisible('auth-username-field'), 'the sign-up fields should be hidden again');

    byId('auth-email').value = 'student@example.com';
    byId('auth-password').value = 'wrongpassword';
    await submitAuth();
    assert.match(text('auth-error'), /incorrect/i);
  });

  await t.test('logging back in restores the history from the server', async () => {
    byId('auth-password').value = PASSWORD;
    await submitAuth();
    await flush();

    assert.ok(isVisible('lobby-screen'));
    assert.equal(text('stat-tests'), '1');
    assert.equal(text('stat-best'), '680');
  });

  await t.test('an empty question bank sends the student back with a notice', async () => {
    backend.setBankEmpty(true);
    click('start-test-btn');
    await wait(100);

    assert.ok(isVisible('lobby-screen'));
    assert.match(text('lobby-notice-slot'), /No generated tests/);
  });
});


test('a saved token signs the student straight back in', async () => {
  const backend = fakeBackend();
  const app = await bootApp({ fetchImpl: backend });
  const { byId, isVisible, text, click, submit } = domHelpers(app.window);

  click('auth-tab-register');
  byId('auth-email').value = 'again@example.com';
  byId('auth-username').value = 'Repeat';
  byId('auth-password').value = PASSWORD;
  byId('auth-confirm').value = PASSWORD;
  submit('auth-form');
  await flush();
  await flush();

  assert.ok(isVisible('lobby-screen'));
  assert.equal(text('lobby-username'), 'Repeat');
  assert.ok(app.window.localStorage.getItem('sat_session_token'), 'the token should be stored');
});
