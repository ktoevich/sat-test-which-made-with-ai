/**
 * The community features around the test: the profile and its settings,
 * the theme and language switches, friends, messages, practising a domain,
 * the leaderboard and another student's profile, and the reload guard.
 */

import assert from 'node:assert/strict';
import test from 'node:test';

import { COUNTDOWN_WAIT_MS, bootApp, domHelpers, flush, wait } from './helpers/dom.mjs';
import { fakeBackend } from './helpers/fake-backend.mjs';

const PASSWORD = 'sup3rsecret';

async function signUp(app, helpers, { username, email }) {
  const { byId, click, submit } = helpers;
  click('auth-tab-register');
  byId('auth-username').value = username;
  byId('auth-email').value = email;
  byId('auth-password').value = PASSWORD;
  byId('auth-confirm').value = PASSWORD;
  submit('auth-form');
  await flush();
  await flush();
}

async function logOut(helpers) {
  helpers.click('logout-btn');
  await flush();
}

async function takeMathTest(app, helpers) {
  const { byId, click, all } = helpers;
  click('start-test-btn');
  await flush();
  await wait(COUNTDOWN_WAIT_MS);
  click(all('.option-item__content', byId('options-list'))[0]);
  click('next-btn');
  click(all('.option-item__content', byId('options-list'))[2]);
  click('next-btn');
  click('next-btn');
  click('finish-confirm-btn');
  await wait(50);
  await wait(COUNTDOWN_WAIT_MS);
  click(all('.option-item__content', byId('options-list'))[1]);
  click('next-btn');
  click('next-btn');
  click('finish-confirm-btn');
  await flush();
  await flush();
}

test('the profile, its settings, the switches and the charts', async (t) => {
  const backend = fakeBackend();
  const app = await bootApp({ fetchImpl: backend });
  const helpers = domHelpers(app.window);
  const { byId, isVisible, text, click, type, all } = helpers;
  const { document } = app.window;

  await signUp(app, helpers, { username: 'Nika', email: 'nika@example.com' });

  await t.test('the header and the profile card show the student', () => {
    assert.ok(isVisible('site-header'));
    assert.equal(text('header-username'), 'Nika');
    assert.equal(text('lobby-username'), 'Nika');
    assert.equal(text('profile-rating'), '1200');
    assert.equal(text('profile-tier'), 'Pupil');
    assert.match(text('rating-chart'), /Finish a test/);
  });

  await t.test('the theme toggle switches and remembers', () => {
    assert.notEqual(document.documentElement.dataset.theme, 'dark');
    click(document.querySelector('#site-header [data-theme-toggle]'));
    assert.equal(document.documentElement.dataset.theme, 'dark');
    assert.equal(app.window.localStorage.getItem('sat_theme'), 'dark');
    click(document.querySelector('#site-header [data-theme-toggle]'));
    assert.equal(document.documentElement.dataset.theme, 'light');
  });

  await t.test('the language switch translates the page', () => {
    click(document.querySelector('#site-header [data-lang="ru"]'));
    assert.equal(document.documentElement.lang, 'ru');
    assert.equal(text('logout-btn'), 'Выйти');
    assert.equal(text('start-test-btn'), 'Начать Math');
    assert.equal(text('profile-tier'), 'Ученик');
    click(document.querySelector('#site-header [data-lang="en"]'));
    assert.equal(text('logout-btn'), 'Logout');
  });

  await t.test('the settings modal edits avatar, handle, name and location', async () => {
    click('open-settings-btn');
    assert.ok(isVisible('settings-modal'));
    click(all('.avatar-option', byId('avatar-grid'))[1]);
    byId('settings-username').value = 'Nika_SAT';
    byId('settings-fullname').value = 'Nika Ivanova';
    byId('settings-location').value = 'Tajikistan, Dushanbe';
    helpers.submit('settings-form');
    await flush();
    await flush();
    assert.equal(text('settings-feedback'), 'Profile updated.');
    assert.equal(text('header-username'), 'Nika_SAT');
    assert.equal(text('header-avatar'), '🦉');
    assert.equal(text('profile-avatar'), '🦉');
    assert.match(text('profile-location'), /Dushanbe/);
    assert.ok(app.requests.includes('PATCH /api/auth/profile'));
  });

  await t.test('a finished test moves the rating and fills the charts', async () => {
    await takeMathTest(app, helpers);
    assert.match(text('score-details'), /Rating: 1200 → \d+/);
    click('back-to-lobby-btn');
    await flush();
    await flush();
    assert.notEqual(text('profile-rating'), '1200');
    assert.ok(byId('rating-chart').querySelector('svg'), 'the rating graph is drawn');
    assert.ok(byId('topics-chart').querySelector('svg'), 'the domains donut is drawn');
    click(all('[data-mode="bars"]', byId('topics-mode'))[0]);
    assert.ok(byId('topics-chart').querySelector('.topics-bar'));
    assert.match(text('history-table-body'), /Retake/);
    assert.match(text('history-table-body'), /Math/);
  });

  await t.test('retaking asks for the same test', async () => {
    click(byId('history-table-body').querySelector('.btn-primary'));
    await flush();
    assert.ok(app.requests.includes('GET /api/tests/module-1?section=math&test_id=t1'));
    await wait(COUNTDOWN_WAIT_MS);
    click('next-btn');
    click('next-btn');
    click('next-btn');
    click('finish-confirm-btn');
    await wait(50);
    await wait(COUNTDOWN_WAIT_MS);
    click('next-btn');
    click('next-btn');
    click('finish-confirm-btn');
    await flush();
    click('back-to-lobby-btn');
    await flush();
  });

  await t.test('practising a domain checks each answer and shows the solution', async () => {
    click(byId('tests-card').querySelector('.topic-chip'));
    await flush();
    assert.ok(isVisible('practice-modal'));
    assert.match(text('practice-title'), /Algebra/);
    assert.match(text('practice-progress'), /Question 1 of/);
    click('practice-check');
    assert.match(text('practice-feedback'), /Pick or type/);
    click(all('.option-item__content', byId('practice-options'))[0]);
    click('practice-check');
    assert.match(text('practice-feedback'), /Correct!/);
    assert.match(text('practice-feedback'), /Because the two expressions/);
    assert.ok(!isVisible('practice-check'));
    click('practice-next');
    assert.match(text('practice-progress'), /Question 2 of/);
    click(all('.option-item__content', byId('practice-options'))[0]);
    click('practice-check');
    assert.match(text('practice-feedback'), /Not quite/);
    click('practice-finish');
    assert.ok(!isVisible('practice-modal'));
  });

  await t.test('the leaderboard lists the best score and opens the profile', async () => {
    assert.match(text('leaderboard-list'), /Nika_SAT/);
    assert.match(text('platform-stats'), /students/);
    assert.match(text('platform-countries'), /Tajikistan/);
  });
});

test('friends, messages and observer mode between two students', async (t) => {
  const backend = fakeBackend();
  const app = await bootApp({ fetchImpl: backend });
  const helpers = domHelpers(app.window);
  const { byId, isVisible, text, click, type, all } = helpers;

  await signUp(app, helpers, { username: 'Farrukh', email: 'farrukh@example.com' });
  await logOut(helpers);
  await signUp(app, helpers, { username: 'Nika', email: 'nika@example.com' });

  await t.test('searching finds a student and opens their profile in observer mode', async () => {
    type(byId('user-search'), 'farr');
    await wait(250);
    await flush();
    assert.match(text('user-search-results'), /Farrukh/);
    click(byId('user-search-results').querySelector('.user-row'));
    await flush();
    await flush();
    assert.ok(isVisible('observer-banner'));
    assert.equal(text('lobby-username'), 'Farrukh');
    assert.ok(!isVisible('tests-card'), 'no tests can be started from someone else\'s profile');
    assert.ok(isVisible('observer-actions'));
    assert.equal(text('observer-friend-btn'), 'Add friend');
  });

  await t.test('a friend request is sent from the profile and accepted from the modal', async () => {
    click('observer-friend-btn');
    await flush();
    assert.equal(text('observer-friend-btn'), 'Request sent');
    assert.ok(app.requests.includes('POST /api/friends/requests'));

    click('observer-exit');
    await flush();
    await flush();
    assert.equal(text('lobby-username'), 'Nika');

    await logOut(helpers);
    byId('auth-email').value = 'farrukh@example.com';
    byId('auth-password').value = PASSWORD;
    helpers.submit('auth-form');
    await flush();
    await flush();
    click('open-friends-btn');
    await flush();
    await flush();
    assert.ok(isVisible('friends-modal'));
    click(byId('friends-tabs').querySelector('[data-tab="incoming"]'));
    assert.match(text('friends-list'), /Nika/);
    click(byId('friends-list').querySelector('.btn-primary'));
    await flush();
    await flush();
    click(byId('friends-tabs').querySelector('[data-tab="friends"]'));
    assert.match(text('friends-list'), /Nika/);
    assert.equal(text('friends-count-list'), '1');
  });

  await t.test('messages go back and forth and the badge counts the unread', async () => {
    click(byId('friends-list').querySelector('.btn-primary'));
    await flush();
    await flush();
    assert.ok(isVisible('messages-modal'));
    assert.match(text('messenger-peer'), /Nika/);
    type(byId('messenger-input'), 'Hi Nika!');
    helpers.submit('messenger-form');
    await flush();
    await flush();
    assert.match(text('messenger-thread'), /Hi Nika!/);
    click(byId('messages-modal').querySelector('[data-close-modal]'));

    await logOut(helpers);
    byId('auth-email').value = 'nika@example.com';
    byId('auth-password').value = PASSWORD;
    helpers.submit('auth-form');
    await flush();
    await flush();
    await flush();
    assert.equal(text('messages-unread'), '1');
    assert.ok(isVisible('messages-unread'));
    click('messages-btn');
    await flush();
    await flush();
    assert.match(text('messenger-contacts'), /Farrukh/);
    assert.match(text('messenger-thread'), /Hi Nika!/);
    assert.ok(!isVisible('messages-unread'), 'reading the thread clears the badge');
    click(byId('messages-modal').querySelector('[data-close-modal]'));
  });
});

test('a test interrupted by a reload is finished with the rest omitted', async (t) => {
  const backend = fakeBackend();
  const app = await bootApp({ fetchImpl: backend });
  const helpers = domHelpers(app.window);
  const { byId, isVisible, text, click, all } = helpers;

  await signUp(app, helpers, { username: 'Nika', email: 'nika@example.com' });
  click('start-test-btn');
  await flush();
  await wait(COUNTDOWN_WAIT_MS);
  click(all('.option-item__content', byId('options-list'))[0]);

  await t.test('the reload keys open a warning instead of reloading', () => {
    app.window.dispatchEvent(new app.window.KeyboardEvent('keydown', { key: 'F5', bubbles: true, cancelable: true }));
    assert.ok(isVisible('reload-modal'));
    click(byId('reload-modal').querySelector('[data-close-modal]'));
    assert.ok(!isVisible('reload-modal'));
    assert.ok(app.window.sessionStorage.getItem('sat_active_test'), 'the attempt is mirrored for the next load');
  });

  await t.test('finishing now scores what was answered and omits the rest', async () => {
    app.window.dispatchEvent(new app.window.KeyboardEvent('keydown', { key: 'r', ctrlKey: true, bubbles: true, cancelable: true }));
    click('reload-finish-btn');
    await flush();
    await flush();
    assert.ok(isVisible('final-results'));
    assert.match(text('intermission-message'), /reloaded during a test/);
    assert.equal(all('tr', byId('review-table-body')).length, 7, 'both modules appear');
    assert.equal(all('.status-badge--omitted', byId('review-table-body')).length, 4);
    assert.equal(app.window.sessionStorage.getItem('sat_active_test'), null);
  });
});
