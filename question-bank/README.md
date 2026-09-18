# SAT Suite Educator Question Bank — local copy

A download of College Board's [SAT Suite Educator Question
Bank](https://satsuiteeducatorquestionbank.collegeboard.org/), kept here so the
bank's own taxonomy and its questions can be queried offline — in particular, to
answer which topics carry graphs.

The site is a React front end over a small JSON API on
`qbank-api.collegeboard.org`; the tools below call that API directly. Nothing is
scraped out of rendered HTML.

## Files

| File | What it is |
| --- | --- |
| `lookup.json` | The bank's own taxonomy: the three assessments, the two tests, and every domain with its skills. |
| `questions-list.json` | The raw catalogue, one row per *(assessment, question)*. 10,458 rows covering 3,767 distinct questions — most questions are offered on more than one assessment. |
| `questions.jsonl` | One downloaded question body per line: stem, stimulus, answer options, correct answer, rationale. Keyed by `_key`. |
| `questions-index.json` | **The one to read.** The catalogue folded to one record per question, joined to its body, with a `graphics` field saying what the question shows. |

### Catalogue size

| Assessment | R&W | Math |
| --- | ---: | ---: |
| SAT | 1,845 | 1,925 |
| PSAT/NMSQT & PSAT 10 | 1,844 | 1,785 |
| PSAT 8/9 | 1,554 | 1,505 |

These are catalogue rows, not distinct items: a handful of questions are listed
twice under one assessment, so SAT Math is 1,925 rows but 1,922 questions — the
number the project's own import works from.

3,767 distinct questions: 3,308 current items keyed by `external_id`, plus 459
legacy items keyed by `ibn`. Both kinds are fetched through the same endpoint.

## The index

```json
{
 "id": "04007e74-f11d-47b3-b918-7efd09473b72",
 "legacy": false,
 "assessments": ["SAT", "PSAT/NMSQT & PSAT 10", "PSAT 8/9"],
 "difficulty": {"SAT": "M", "PSAT/NMSQT & PSAT 10": "H", "PSAT 8/9": "H"},
 "test": "R&W",
 "domain": "Information and Ideas",
 "skill": "Command of Evidence",
 "graphics": {
  "fetched": true,
  "graph": true,
  "kinds": ["Bar graph"],
  "figures": [{"kind": "Bar graph", "title": "Spider Population Count", "label": "Bar graph titled ..."}],
  "table": false
 }
}
```

Domain and skill are fixed per question; `difficulty` is not — the same item can
be Medium on the SAT and Hard on the PSAT 8/9, so it is recorded per assessment.

Questions whose body has not been downloaded yet carry `"graphics": {"fetched":
false}` rather than being left out, so the index always covers the whole
catalogue.

## How a graph is recognised

Every figure is an inline `<svg>` whose `aria-label` names it in a fixed house
style, and each is paired with a "Long description for ..." block repeating the
content as prose:

> `Bar graph titled Spider Population Count. The horizontal axis is labeled Day of experiment. 4 data categories are shown. The vertical axis is labeled Spider count. It ranges from 0 to 90 in increments of 10.`

`tools/graphics.py` classifies on that label, so a question counts as having a
graph only where the College Board's own wording says so — no image decoding.
The kinds it distinguishes:

- **Graphs** (`graphics.graph` is true) — Bar graph, Line graph, Scatterplot,
  Histogram, Dot plot, Box plot, Circle graph, Coordinate-plane graph, Number line.
- **Not graphs, but reported** — Geometric figure, Other figure, and `table`,
  which is tracked separately because tables arrive as `<figure class="table">`
  rather than as art.

The chart vocabulary is confirmed against downloaded Reading and Writing items.
The geometry and coordinate-plane branches matter mostly for Math, which is
later in the download order — check a sample of Math records once the crawl has
covered them.

## Refreshing

```sh
cd question-bank/tools
python3 fetch_lists.py      # catalogue + taxonomy
python3 fetch_questions.py  # bodies; resumable, skips what questions.jsonl has
python3 build_index.py      # rebuild questions-index.json, print graphs by topic
```

`build_index.py` also prints the share of questions carrying a graph for every
topic, worst-to-best.

On macOS the stock Python has no CA bundle and every call fails the TLS
handshake; prefix with `SSL_CERT_FILE=/etc/ssl/cert.pem`.

**The bank rate-limits by IP, at the host level.** Crawling with a dozen threads
got `qbank-api.collegeboard.org` to stop answering this machine entirely — the
site itself kept loading, the API did not, for well over half an hour.
`fetch_questions.py` therefore uses two workers with a pause between calls, and
waits out a block instead of retrying into it. A full download takes hours; it
resumes, so running it again after an interruption costs nothing.
