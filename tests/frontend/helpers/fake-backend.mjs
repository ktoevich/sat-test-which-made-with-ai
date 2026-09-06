/**
 * An in-memory stand-in for the API, so the UI tests exercise the real
 * request/response shapes without running a server.
 */

import { MODULE_1, MODULE_2 } from './fixtures.mjs';

const json = (status, body) => ({
  ok: status < 400,
  status,
  json: async () => body,
});

const fail = (status, code, message) => json(status, { error: { code, message } });

export function fakeBackend({ bankEmpty = false } = {}) {
  const state = { bankEmpty };
  const users = new Map();
  const sessions = new Map();
  const attempts = new Map();
  let nextUserId = 1;
  let nextAttemptId = 1;

  const userFor = (headers) => {
    const header = headers?.Authorization ?? '';
    const token = header.startsWith('Bearer ') ? header.slice(7) : '';
    const userId = sessions.get(token);
    return userId ? users.get(userId) : null;
  };

  const publicUser = (user) => ({
    id: user.id,
    email: user.email,
    username: user.username,
    created_at: user.created_at,
    last_login_at: user.last_login_at,
    is_disabled: false,
  });

  const issueToken = (user) => {
    const token = `token-${user.id}-${sessions.size}`;
    sessions.set(token, user.id);
    return token;
  };

  /** @param {URL} url */
  function handle(url, { method = 'GET', headers, body } = {}) {
    const path = url.pathname;
    const payload = body ? JSON.parse(body) : {};

    if (path === '/api/auth/register') {
      const email = String(payload.email).trim().toLowerCase();
      if (users.has(email)) {
        return fail(409, 'email_taken', 'An account with this email already exists.');
      }
      if (String(payload.password).length < 8) {
        return fail(422, 'validation_failed', 'Password must be at least 8 characters.');
      }
      const user = {
        id: nextUserId,
        email,
        username: payload.username,
        password: payload.password,
        created_at: new Date().toISOString(),
        last_login_at: null,
      };
      users.set(email, user);
      users.set(nextUserId, user);
      attempts.set(nextUserId, []);
      nextUserId += 1;
      return json(201, { token: issueToken(user), user: publicUser(user) });
    }

    if (path === '/api/auth/login') {
      const user = users.get(String(payload.email).trim().toLowerCase());
      if (!user || user.password !== payload.password) {
        return fail(401, 'invalid_credentials', 'Email or password is incorrect.');
      }
      user.last_login_at = new Date().toISOString();
      return json(200, { token: issueToken(user), user: publicUser(user) });
    }

    if (path === '/api/auth/logout') {
      const header = headers?.Authorization ?? '';
      sessions.delete(header.startsWith('Bearer ') ? header.slice(7) : '');
      return json(204, null);
    }

    if (path === '/api/auth/me') {
      const user = userFor(headers);
      return user ? json(200, { user: publicUser(user) }) : fail(401, 'not_authenticated', 'Sign in.');
    }

    if (path === '/api/attempts') {
      const user = userFor(headers);
      if (!user) return fail(401, 'not_authenticated', 'Sign in.');
      const history = attempts.get(user.id);

      if (method === 'POST') {
        const attempt = {
          id: nextAttemptId,
          taken_at: new Date().toISOString(),
          score: payload.score,
          correct: payload.correct,
          total: payload.total,
          details: payload.details ?? [],
        };
        nextAttemptId += 1;
        history.unshift(attempt);
        return json(201, { attempt });
      }

      const scores = history.map((a) => a.score);
      return json(200, {
        attempts: history,
        summary: {
          taken: history.length,
          best: scores.length ? Math.max(...scores) : null,
          average: scores.length
            ? Math.round(scores.reduce((sum, value) => sum + value, 0) / scores.length)
            : null,
        },
      });
    }

    if (path.startsWith('/api/tests/')) {
      if (state.bankEmpty) {
        return fail(503, 'bank_empty', 'No generated tests are available yet.');
      }
      return path.endsWith('module-1')
        ? json(200, { test_id: 't1', module: 1, questions: MODULE_1 })
        : json(200, { test_id: 't1', module: 2, questions: MODULE_2 });
    }

    return fail(404, 'not_found', `No API endpoint at ${path}`);
  }

  /** Flip the question bank empty without losing the accounts already created. */
  handle.setBankEmpty = (value) => {
    state.bankEmpty = value;
  };

  return handle;
}
