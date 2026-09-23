# Standalone SAT Math test

Open `index.html` in a browser and module 1 starts at once — no account, no
server. Double-clicking the file is enough; nothing here uses ES modules or
`fetch`, which browsers block on `file://`.

- 14 tests, each the digital SAT's shape: two modules of 22 questions (17
  multiple choice, 5 grid-ins), 35 minutes each. Module 2 is the harder one
  after 15 or more right in module 1.
- Every question is an official College Board item from the SAT Suite
  Educator Question Bank (see `question-bank/README.md`), with its rationale,
  shown on the results page.
- Each visit starts the next test; `index.html?test=3` opens a given one. A
  reload carries on with the attempt in progress, clock included.
- Formulas render offline (KaTeX is in `vendor/`); the Desmos calculator needs
  the internet.

## Building

`questions.js` is generated and kept out of git — it is College Board content,
like the rest of the downloaded bank. Build it from the local bank:

```sh
python3 standalone-test/build.py
```

The folder can then be copied anywhere — a USB stick, a classroom laptop — as
long as `questions.js` and `vendor/` travel with `index.html`.
