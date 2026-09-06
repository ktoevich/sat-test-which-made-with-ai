# SAT Practice — Digital SAT Math Mock Test

Adaptive two-module practice test for the digital SAT math section:
module 1 is served from a pre-generated question bank, and the difficulty of
module 2 follows how the student did in module 1.

- **Backend** — Flask API that serves modules from a JSON question bank.
- **Frontend** — dependency-free ES modules (no build step) plus KaTeX for formulas.

## Requirements

- Python 3.10+
- A modern browser (the frontend uses native ES modules)

## Quick start

```bash
make install   # creates backend/.venv and installs dependencies
make run       # http://127.0.0.1:5000
```

`make run` starts Flask, which serves both the API and the frontend, so a single
URL is enough. To do it by hand:

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python wsgi.py
```

### Running the frontend separately

Set `SERVE_FRONTEND=0` for the backend and host `frontend/` with any static
server. The page then talks to `http://127.0.0.1:5000/api` by default; point it
elsewhere through the meta tag in `frontend/index.html`:

```html
<meta name="sat:api-base" content="https://api.example.com/api">
```

Open the frontend over `http://`, not `file://` — browsers block ES module
imports on the `file:` scheme.

## Tests

```bash
make test            # both suites
make test-backend    # pytest, in backend/
make test-frontend   # jsdom walk-through of the whole UI, in frontend/
```

The backend suite runs against SQLite by default. To check the code path the
deployment actually uses, point it at a Postgres database:

```bash
cd backend
TEST_DATABASE_URL=postgres://... .venv/bin/python -m pytest
```

The frontend ships as plain ES modules and needs no build step; `npm` is only
used to pull in `jsdom` for the tests.

## Project layout

```
backend/
  app/
    __init__.py          application factory
    config.py            environment-driven settings
    extensions.py        Flask extension instances
    api/
      routes.py          test endpoints
      auth.py            registration, login, session
      attempts.py        test history
      errors.py          shared JSON error envelope
    db.py                SQLite/PostgreSQL connections and schema
    security.py          password hashing and session tokens
    cli_users.py         the `users` admin commands
    services/
      accounts.py        registration, login, sessions
      attempts.py        saved test history
      question_bank.py   reads and caches the bundle file
      test_builder.py    orders and numbers a module's questions
    bank/
      taxonomy.py        the Digital SAT blueprint: domains, skills, shares
      schema.py          validation rules for a bank file
      importer.py        normalises an export you already have
      generator.py       builds original questions from templates
      assembler.py       turns a pool of questions into bundles
      templates/         the question templates, by domain
      latex.py           LaTeX formatting helpers
    cli.py               validate / stats / generate / import commands
  data/
    tests_bundle_cache.json   the question bank
  tests/                 pytest suite
  wsgi.py                dev server / gunicorn entry point

frontend/
  index.html
  styles/
    main.css             the only stylesheet the page links
    base/                tokens, reset, utilities, animations
    components/          buttons, forms, tables, modals, badges
    screens/             auth, lobby, exam, results, loading
  src/
    main.js              entry point
    app.js               wires screens together
    config.js            API base URL, timings, score bounds
    api/                 fetch wrapper and endpoint functions
    core/                DOM, storage, scoring, question helpers
    features/
      auth/              sign-in and sign-up
      lobby/             dashboard and history
      exam/              state, timer, navigator, question view, controller
      results/           score screen, solution and attempt modals
    ui/                  screen switching, loading overlay, modals
  tests/                 jsdom end-to-end suite
  package.json           test-only tooling (jsdom); the app needs no build
```

## API

Base path `/api`. Errors use one envelope: `{"error": {"code", "message"}}`.

| Method | Path                                     | Description |
| ------ | ---------------------------------------- | ----------- |
| GET    | `/api/health`                            | Liveness plus the number of available tests |
| GET    | `/api/tests/module-1`                    | Starts an attempt; returns `test_id` and module 1 |
| GET    | `/api/tests/module-2?test_id=&target=`   | Module 2 for that attempt; `target` is `HIGHER` or `LOWER` |
| POST   | `/api/auth/register`                     | Create an account; returns a session token |
| POST   | `/api/auth/login`                        | Sign in; returns a session token |
| POST   | `/api/auth/logout`                       | End the current session |
| GET    | `/api/auth/me`                           | The signed-in user |
| GET    | `/api/attempts`                          | That user's history and summary |
| POST   | `/api/attempts`                          | Save a finished attempt |

Everything under `/api/auth/me`, `/api/auth/logout` and `/api/attempts` needs an
`Authorization: Bearer <token>` header.

Response shape:

```json
{ "test_id": "sat-questionbank-export-01", "module": 1, "questions": [ ... ] }
```

Error codes: `bank_empty` (503, nothing generated yet), `test_not_found` (404),
`invalid_request` (422), `not_found` (404).

## Building the question bank

Everything below runs from `backend/` with the virtualenv active
(`.venv/bin/python -m app.cli ...`), or through the `make` targets.

### The blueprint

`app/bank/taxonomy.py` encodes the published structure of the Digital SAT math
section: two 35-minute modules of 22 questions, the four content domains, their
approximate shares of the test, and the skills tested under each. On a 44-question
section those shares work out to 15 / 15 / 7 / 7 questions.

| Domain | Share | Skills |
| ------ | ----- | ------ |
| Algebra | ~35% | 5 |
| Advanced Math | ~35% | 3 |
| Problem-Solving and Data Analysis | ~15% | 7 |
| Geometry and Trigonometry | ~15% | 4 |

Templates declare which domain and skill they cover, and the test suite fails if
a template names something outside the blueprint or if a skill has no template,
so coverage cannot silently regress.

### Generate original questions

`app.cli generate` builds questions from this project's own templates — 20 of
them, at least one per skill in the blueprint, each parameterised by difficulty.
Question selection chases the published domain shares, so a generated bank lands
on the 35/35/15/15 split rather than whatever the templates happen to produce.
Nothing is copied from a third-party question bank.

```bash
make generate BUNDLES=3
# or
cd backend && .venv/bin/python -m app.cli generate --bundles 3 --seed 42 --force
```

| Flag | Default | Meaning |
| ---- | ------- | ------- |
| `--bundles` | `1` | How many complete tests to build |
| `--module-size` | `22` | Questions per module |
| `--spr` | `6` | Grid-in questions per module |
| `--seed` | random | Makes the output reproducible |
| `-o`, `--output` | `data/tests_bundle_cache.json` | Where to write |
| `--force` | off | Allow overwriting an existing file |

Module 1 uses a mixed difficulty spread; `module_2_HIGHER` skews hard and
`module_2_LOWER` skews easy, which is what makes the adaptive second module
feel different.

### Import questions you already have

`app.cli import` reads a `.json` or `.csv` file **from your own disk** and maps
it onto this project's format — it never downloads anything. Common column names
(`stem`/`question`/`text`, `correct_answer`/`key`, `option_a`…`option_d`,
`choices`, `level`, `explanation`) are recognised automatically, answers given as
a letter, a zero-based index or the full option text are all resolved to a
letter, and the question type is inferred when it is missing.

```bash
cd backend && .venv/bin/python -m app.cli import ~/export.csv --bundles 2 --force
```

Add `--skip-invalid` to drop unusable rows instead of failing on the first one.

### Check what you have

```bash
make validate   # every problem, addressed as $[0].module_1[3].answer
make stats      # counts by module, type, difficulty and domain
```

Validation also runs automatically before `generate` or `import` writes a file,
so a broken bank never reaches `data/`.

### Adding a template

Subclass `Template` in the matching `app/bank/templates/*.py` module, implement
`build(rng, qtype, difficulty)`, and append the instance to that module's
`TEMPLATES` list. Its `domain` and `skill` must come from `taxonomy.py`. `tests/test_generator.py` then fuzzes it automatically: every
template is built 120 times per type and difficulty and checked against the
schema, including that its multiple-choice options stay distinct.

## Accounts

Accounts, sessions and test history live in a SQLite file, `backend/data/app.db`,
created automatically on first run. Set `DATABASE_URL` to a `postgres://` URL and
the same code uses PostgreSQL instead — required for serverless hosts, which have
no persistent disk.

Passwords are stored as **PBKDF2-HMAC-SHA256 hashes** with a per-password salt
and 600,000 iterations. They are one-way: nobody, including you, can read a
password back out of the database. A login issues a random session token, and
only a SHA-256 fingerprint of that token is stored, so a database dump cannot be
replayed as a login. The browser keeps nothing but the token.

### Managing accounts

```bash
cd backend
.venv/bin/python -m app.cli users list                       # everyone, newest first
.venv/bin/python -m app.cli users list --search nika         # find a forgotten login
.venv/bin/python -m app.cli users show nika@example.com      # one account and its attempts
.venv/bin/python -m app.cli users reset-password nika@example.com
.venv/bin/python -m app.cli users disable nika@example.com   # block sign-in
.venv/bin/python -m app.cli users enable  nika@example.com
.venv/bin/python -m app.cli users delete  nika@example.com --yes
```

**Forgot the login?** `users list --search` matches part of an email or username,
so you can find which address someone signed up with.

**Forgot the password?** It cannot be looked up — `reset-password` issues a new
temporary one, prints it once, and signs out every existing session for that
account. Pass `--password` to set a specific one instead.

Deleting an account also removes its sessions and attempts.

## Question bank format

`backend/data/tests_bundle_cache.json` holds a list of bundles:

```json
[
  {
    "test_id": "sat-questionbank-export-01",
    "module_1":        [ /* questions */ ],
    "module_2_HIGHER": [ /* questions */ ],
    "module_2_LOWER":  [ /* questions */ ]
  }
]
```

A question:

```json
{
  "question_id": "b86123af",
  "domain": "Algebra",
  "skill": "Systems of two linear equations in two variables",
  "difficulty": "Easy",
  "type": "MCQ",
  "text": "...",
  "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
  "answer": "B",
  "rationale": "...",
  "image": null
}
```

- `type` is `MCQ` (multiple choice) or `SPR` (student-produced response).
- `difficulty` is `Easy`, `Medium` or `Hard`; it drives the order inside a module.
- `image` is optional: either raw SVG/HTML, or a coordinate-grid descriptor
  `{ "xEnd": 10, "yEnd": 10, "step": 2, "draw": "<svg fragment>" }`.

The file is re-read automatically when its modification time changes, so a
regenerated bank is picked up without restarting the server.

## Configuration

Backend settings come from environment variables — see `backend/.env.example`.

| Variable             | Default                        | Purpose |
| -------------------- | ------------------------------ | ------- |
| `FLASK_ENV`          | `development`                  | `development` / `production` / `testing` |
| `HOST`, `PORT`       | `127.0.0.1`, `5000`            | Bind address for `wsgi.py` |
| `QUESTION_BANK_PATH` | `backend/data/tests_bundle_cache.json` | Question bank location |
| `CORS_ORIGINS`       | `*`                            | Comma-separated allowed browser origins |
| `SERVE_FRONTEND`     | `1` (`0` in production)        | Also serve `frontend/` from Flask |
| `DATABASE_URL`       | unset                          | Postgres URL; overrides `DATABASE_PATH`. `POSTGRES_URL` also works |
| `DATABASE_PATH`      | `backend/data/app.db`          | SQLite file used when no URL is set |
| `PASSWORD_ITERATIONS`| `600000`                       | PBKDF2 rounds |

## Deployment

### Vercel

The repository is ready to deploy as-is:

- `index.py` exposes the Flask `app` Vercel looks for at the repository root.
- `build_public.py` copies `frontend/` into `public/`, which Vercel serves from
  the CDN, so pages and assets never wake a function.
- `vercel.json` wires the build command and the function.
- `.vercelignore` keeps tests, virtualenvs and the local database out.

**A database is required.** Serverless functions get a read-only, throwaway
filesystem, so the SQLite file used locally cannot persist there — accounts and
history would disappear between requests. Create a Postgres database in the
Vercel dashboard (Storage → Create → Postgres) and attach it to the project.
That sets `POSTGRES_URL` automatically, which the app picks up; use the pooled
URL, since every request opens its own connection.

Then set one more environment variable in the project settings:

| Variable | Value | Why |
| -------- | ----- | --- |
| `FLASK_ENV` | `production` | Turns off debug and lets the CDN serve the frontend |
| `CORS_ORIGINS` | your deployment origin | Replaces the `*` default |

Deploy by connecting the Git repository, or from the CLI:

```bash
vercel deploy
```

The schema is created on the first request, so there is no migration step.

Run the admin commands against the deployed database by passing its URL:

```bash
cd backend
.venv/bin/python -m app.cli users --database "$POSTGRES_URL" list
```

### Any other host

```bash
cd backend
FLASK_ENV=production DATABASE_URL=postgres://... \
  .venv/bin/gunicorn --bind 0.0.0.0:8000 "wsgi:app"
```

Set `SERVE_FRONTEND=1` if you want Flask to serve `frontend/` itself instead of
putting it behind a CDN, and set `CORS_ORIGINS` to the real frontend origin.

## Known limitations

- There is no email delivery, so a password reset is an admin running
  `users reset-password` and passing the temporary password on by hand.
- Every account has the same rights; there is no admin role in the app itself.
  Account management is deliberately CLI-only, on the machine holding the
  database.
- Sign-in has no rate limiting. Put the app behind a proxy that provides it
  before exposing it to the internet.
- The question bank is a static file. `app.cli generate` fills it with original
  template-built questions; `app.cli import` converts an export you supply.
- Advanced Math carries ~35% of the section but has only 3 skills, so the
  generator leans hard on its four templates. Questions there repeat in shape
  more than in other domains; more Advanced Math templates would fix it.
