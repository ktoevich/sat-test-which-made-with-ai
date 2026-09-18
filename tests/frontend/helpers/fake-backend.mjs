/**
 * An in-memory stand-in for the API, so the UI tests exercise the real
 * request/response shapes without running a server.
 */

import { MODULE_1, MODULE_2, READING_MODULE_1, READING_MODULE_2 } from './fixtures.mjs';

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

  const communityUser = (user) => ({
    id: user.id,
    username: user.username,
    avatar: user.avatar ?? '',
    full_name: user.full_name ?? '',
    location: user.location ?? '',
    rating: user.rating ?? 1200,
    max_rating: user.max_rating ?? 1200,
    top_score: user.top_score ?? null,
    // The band of the best score, as the API works it out.
    tier: [[700, 'elite'], [600, 'advanced'], [500, 'intermediate']].find(([from]) => (user.top_score ?? 0) >= from)?.[1] ?? 'basic',
    created_at: user.created_at,
  });

  const publicUser = (user) => ({
    ...communityUser(user),
    email: user.email,
    last_login_at: user.last_login_at,
    is_disabled: false,
  });

  const friendships = [];
  const messages = [];
  const notifications = [];
  let nextRequestId = 1;
  let nextMessageId = 1;
  let nextNotificationId = 1;
  const notify = (userId, kind, actorId, refId) => {
    notifications.push({ id: nextNotificationId++, user_id: userId, actor_id: actorId, kind, ref_id: refId, created_at: new Date().toISOString(), read_at: null });
  };
  /** A request was accepted: its notification is read, and the asker hears back. */
  const accepted = (row) => {
    notifications.forEach((n) => { if (n.kind === 'friend_request' && n.ref_id === row.id) n.read_at ??= new Date().toISOString(); });
    notify(row.from, 'friend_accepted', row.to, row.id);
  };
  const relationship = (a, b) => {
    if (a === b) return 'self';
    const row = friendships.find((f) => (f.from === a && f.to === b) || (f.from === b && f.to === a));
    if (!row) return 'none';
    if (row.status === 'accepted') return 'friends';
    return row.from === a ? 'outgoing' : 'incoming';
  };
  const summaryOf = (history) => {
    const aggregate = (items) => {
      const scores = items.map((a) => a.score);
      return {
        taken: items.length,
        best: scores.length ? Math.max(...scores) : null,
        average: scores.length ? Math.round(scores.reduce((sum, value) => sum + value, 0) / scores.length) : null,
      };
    };
    return {
      ...aggregate(history),
      by_section: {
        math: aggregate(history.filter((a) => a.section === 'math')),
        reading: aggregate(history.filter((a) => a.section === 'reading')),
      },
    };
  };
  const analyticsOf = (history) => ({
    rating_points: [...history].reverse().map((a) => ({
      attempt_id: a.id, taken_at: a.taken_at, section: a.section, score: a.score, correct: a.correct,
      total: a.total, rating_before: a.rating_before, rating_after: a.rating_after,
    })),
    topics: history.length ? [{ section: 'math', domain: 'Algebra', correct: 3, seen: 4 }] : [],
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
        avatar: '',
        full_name: '',
        location: '',
        rating: 1200,
        max_rating: 1200,
        settings: {},
      };
      users.set(email, user);
      users.set(nextUserId, user);
      attempts.set(nextUserId, []);
      nextUserId += 1;
      return json(201, { token: issueToken(user), user: publicUser(user), settings: user.settings });
    }

    if (path === '/api/auth/login') {
      const user = users.get(String(payload.email).trim().toLowerCase());
      if (!user || user.password !== payload.password) {
        return fail(401, 'invalid_credentials', 'Email or password is incorrect.');
      }
      user.last_login_at = new Date().toISOString();
      return json(200, { token: issueToken(user), user: publicUser(user), settings: user.settings });
    }

    if (path === '/api/auth/logout') {
      const header = headers?.Authorization ?? '';
      sessions.delete(header.startsWith('Bearer ') ? header.slice(7) : '');
      return json(204, null);
    }

    if (path === '/api/auth/me') {
      const user = userFor(headers);
      return user ? json(200, { user: publicUser(user), settings: user.settings }) : fail(401, 'not_authenticated', 'Sign in.');
    }

    if (path === '/api/auth/settings') {
      const user = userFor(headers);
      if (!user) return fail(401, 'not_authenticated', 'Sign in.');
      if (method === 'PATCH') {
        const allowed = { theme: ['light', 'dark'], language: ['en', 'ru'] };
        const bad = Object.entries(payload).some(([key, value]) => !allowed[key]?.includes(value));
        if (bad || !Object.keys(payload).length) return fail(422, 'validation_failed', 'Unknown setting.');
        user.settings = { ...user.settings, ...payload };
      }
      return json(200, { settings: user.settings });
    }

    if (path === '/api/notifications') {
      const user = userFor(headers);
      if (!user) return fail(401, 'not_authenticated', 'Sign in.');
      const mine = notifications.filter((n) => n.user_id === user.id);
      return json(200, {
        notifications: [...mine].reverse().map((n) => ({
          id: n.id,
          kind: n.kind,
          ref_id: n.ref_id,
          created_at: n.created_at,
          read: Boolean(n.read_at),
          pending: n.kind === 'friend_request' && friendships.some((f) => f.id === n.ref_id && f.status === 'pending'),
          user: communityUser(users.get(n.actor_id)),
        })),
        unread: mine.filter((n) => !n.read_at).length,
      });
    }

    if (path === '/api/notifications/read') {
      const user = userFor(headers);
      if (!user) return fail(401, 'not_authenticated', 'Sign in.');
      notifications.forEach((n) => {
        if (n.user_id === user.id && (payload.id === undefined || n.id === payload.id)) n.read_at ??= new Date().toISOString();
      });
      return json(200, { unread: notifications.filter((n) => n.user_id === user.id && !n.read_at).length });
    }

    if (path === '/api/auth/profile') {
      const user = userFor(headers);
      if (!user) return fail(401, 'not_authenticated', 'Sign in.');
      if (payload.username !== undefined && !String(payload.username).trim()) {
        return fail(422, 'validation_failed', 'Username must be 1-40 characters.');
      }
      for (const key of ['username', 'avatar', 'full_name', 'location']) {
        if (payload[key] !== undefined) user[key] = String(payload[key]).trim();
      }
      return json(200, { user: publicUser(user) });
    }

    if (path === '/api/attempts') {
      const user = userFor(headers);
      if (!user) return fail(401, 'not_authenticated', 'Sign in.');
      const history = attempts.get(user.id);

      if (method === 'POST') {
        const before = user.rating;
        const after = Math.max(800, before + Math.round((payload.score - 600) * 0.45));
        user.rating = after;
        user.max_rating = Math.max(user.max_rating, after);
        user.top_score = Math.max(user.top_score ?? 0, payload.score);
        const attempt = {
          id: nextAttemptId,
          taken_at: new Date().toISOString(),
          section: payload.section ?? 'math',
          score: payload.score,
          correct: payload.correct,
          total: payload.total,
          details: payload.details ?? [],
          test_id: payload.test_id ?? '',
          target: payload.target ?? '',
          time_spent: payload.time_spent ?? 0,
          rating_before: before,
          rating_after: after,
        };
        nextAttemptId += 1;
        history.unshift(attempt);
        return json(201, { attempt });
      }

      return json(200, { attempts: history, summary: summaryOf(history) });
    }

    if (path === '/api/users/search') {
      if (!userFor(headers)) return fail(401, 'not_authenticated', 'Sign in.');
      const q = (url.searchParams.get('q') ?? '').toLowerCase();
      const found = [...new Set(users.values())]
        .filter((u) => !q || u.username.toLowerCase().includes(q) || (u.full_name ?? '').toLowerCase().includes(q))
        .map(communityUser);
      return json(200, { users: found });
    }

    const userMatch = /^\/api\/users\/(\d+)$/.exec(path);
    if (userMatch) {
      const viewer = userFor(headers);
      if (!viewer) return fail(401, 'not_authenticated', 'Sign in.');
      const target = users.get(Number(userMatch[1]));
      if (!target) return fail(404, 'user_not_found', 'That student does not exist.');
      const history = (attempts.get(target.id) ?? []).map(({ details, ...rest }) => rest);
      return json(200, {
        user: communityUser(target),
        summary: summaryOf(history),
        history,
        analytics: analyticsOf(history),
        friends_count: friendships.filter((f) => f.status === 'accepted' && (f.from === target.id || f.to === target.id)).length,
        relationship: relationship(viewer.id, target.id),
      });
    }

    if (path === '/api/leaderboard') {
      const section = url.searchParams.get('section') ?? 'math';
      const rows = [];
      for (const user of new Set(users.values())) {
        const best = (attempts.get(user.id) ?? []).filter((a) => a.section === section).sort((a, b) => b.score - a.score)[0];
        if (best) rows.push({ user: communityUser(user), score: best.score, time_spent: best.time_spent, taken_at: best.taken_at, correct: best.correct, total: best.total, target: best.target });
      }
      rows.sort((a, b) => b.score - a.score);
      return json(200, { section, leaderboard: rows.map((row, index) => ({ rank: index + 1, ...row })) });
    }

    if (path === '/api/stats') {
      const all = [...attempts.values()].flat();
      return json(200, {
        students: new Set(users.values()).size,
        tests_taken: all.length,
        by_section: {
          math: { taken: all.filter((a) => a.section === 'math').length, average: 650, perfect_scorers: 0 },
          reading: { taken: all.filter((a) => a.section === 'reading').length, average: null, perfect_scorers: 0 },
        },
        countries: [{ name: 'Tajikistan', students: 1, flag: '🇹🇯' }],
      });
    }

    if (path === '/api/friends') {
      const user = userFor(headers);
      if (!user) return fail(401, 'not_authenticated', 'Sign in.');
      const entry = (f, otherId) => ({ request_id: f.id, since: f.created_at, user: communityUser(users.get(otherId)) });
      return json(200, {
        friends: friendships.filter((f) => f.status === 'accepted' && (f.from === user.id || f.to === user.id)).map((f) => entry(f, f.from === user.id ? f.to : f.from)),
        incoming: friendships.filter((f) => f.status === 'pending' && f.to === user.id).map((f) => entry(f, f.from)),
        outgoing: friendships.filter((f) => f.status === 'pending' && f.from === user.id).map((f) => entry(f, f.to)),
      });
    }

    if (path === '/api/friends/requests' && method === 'POST') {
      const user = userFor(headers);
      if (!user) return fail(401, 'not_authenticated', 'Sign in.');
      const other = Number(payload.user_id);
      if (!users.get(other)) return fail(404, 'user_not_found', 'That student does not exist.');
      const existing = friendships.find((f) => (f.from === user.id && f.to === other) || (f.from === other && f.to === user.id));
      if (existing) {
        if (existing.status === 'pending' && existing.to === user.id) {
          existing.status = 'accepted';
          accepted(existing);
          return json(201, { relationship: 'friends' });
        }
        return fail(409, 'not_allowed', 'Already there.');
      }
      const row = { id: nextRequestId++, from: user.id, to: other, status: 'pending', created_at: new Date().toISOString() };
      friendships.push(row);
      notify(other, 'friend_request', user.id, row.id);
      return json(201, { relationship: 'outgoing' });
    }

    const acceptMatch = /^\/api\/friends\/requests\/(\d+)\/accept$/.exec(path);
    if (acceptMatch) {
      const user = userFor(headers);
      const row = friendships.find((f) => f.id === Number(acceptMatch[1]));
      if (!row || row.to !== user?.id) return fail(409, 'not_allowed', 'No such request.');
      row.status = 'accepted';
      accepted(row);
      return json(200, { relationship: 'friends' });
    }

    const requestMatch = /^\/api\/friends\/requests\/(\d+)$/.exec(path);
    if (requestMatch && method === 'DELETE') {
      const id = Number(requestMatch[1]);
      const index = friendships.findIndex((f) => f.id === id);
      if (index >= 0) friendships.splice(index, 1);
      for (let i = notifications.length - 1; i >= 0; i -= 1) {
        if (notifications[i].kind === 'friend_request' && notifications[i].ref_id === id) notifications.splice(i, 1);
      }
      return json(204, null);
    }

    const unfriendMatch = /^\/api\/friends\/(\d+)$/.exec(path);
    if (unfriendMatch && method === 'DELETE') {
      const user = userFor(headers);
      const other = Number(unfriendMatch[1]);
      const index = friendships.findIndex((f) => f.status === 'accepted' && ((f.from === user.id && f.to === other) || (f.from === other && f.to === user.id)));
      if (index >= 0) friendships.splice(index, 1);
      return json(204, null);
    }

    if (path === '/api/messages') {
      const user = userFor(headers);
      if (!user) return fail(401, 'not_authenticated', 'Sign in.');
      const seen = new Map();
      [...messages].reverse().forEach((m) => {
        if (m.sender_id !== user.id && m.recipient_id !== user.id) return;
        const otherId = m.sender_id === user.id ? m.recipient_id : m.sender_id;
        if (!seen.has(otherId)) seen.set(otherId, { user: communityUser(users.get(otherId)), last_message: { body: m.body, sent_at: m.sent_at, mine: m.sender_id === user.id }, unread: 0 });
        if (m.recipient_id === user.id && !m.read_at) seen.get(otherId).unread += 1;
      });
      return json(200, { conversations: [...seen.values()], unread: messages.filter((m) => m.recipient_id === user.id && !m.read_at).length });
    }

    const threadMatch = /^\/api\/messages\/(\d+)$/.exec(path);
    if (threadMatch) {
      const user = userFor(headers);
      if (!user) return fail(401, 'not_authenticated', 'Sign in.');
      const other = users.get(Number(threadMatch[1]));
      if (!other) return fail(404, 'user_not_found', 'That student does not exist.');
      if (method === 'POST') {
        const body = String(payload.body ?? '').trim();
        if (!body) return fail(422, 'validation_failed', 'Write something first.');
        const message = { id: nextMessageId++, sender_id: user.id, recipient_id: other.id, body, sent_at: new Date().toISOString(), read_at: null };
        messages.push(message);
        return json(201, { message });
      }
      messages.forEach((m) => { if (m.recipient_id === user.id && m.sender_id === other.id) m.read_at = new Date().toISOString(); });
      const thread = messages.filter((m) => (m.sender_id === user.id && m.recipient_id === other.id) || (m.sender_id === other.id && m.recipient_id === user.id));
      return json(200, { user: communityUser(other), messages: thread });
    }

    if (path === '/api/practice') {
      const section = url.searchParams.get('section');
      const questions = (section === 'reading' ? READING_MODULE_1 : MODULE_1).map((q, index) => ({ ...q, id: index + 1 }));
      return json(200, { section, domain: url.searchParams.get('domain'), questions });
    }

    if (path.startsWith('/api/tests/')) {
      if (state.bankEmpty) {
        return fail(503, 'bank_empty', 'No generated tests are available yet.');
      }
      // Module 1 names its section; module 2 belongs to the test it continues.
      const reading = path.endsWith('module-1')
        ? url.searchParams.get('section') === 'reading'
        : url.searchParams.get('test_id') === 'r1';
      if (reading) {
        return path.endsWith('module-1')
          ? json(200, { test_id: 'r1', section: 'reading', module: 1, questions: READING_MODULE_1 })
          : json(200, { test_id: 'r1', section: 'reading', module: 2, questions: READING_MODULE_2 });
      }
      return path.endsWith('module-1')
        ? json(200, { test_id: 't1', section: 'math', module: 1, questions: MODULE_1 })
        : json(200, { test_id: 't1', section: 'math', module: 2, questions: MODULE_2 });
    }

    return fail(404, 'not_found', `No API endpoint at ${path}`);
  }

  /** Flip the question bank empty without losing the accounts already created. */
  handle.setBankEmpty = (value) => {
    state.bankEmpty = value;
  };

  return handle;
}
