"""Convert the downloaded questions into this project's question format.

Reads ``questions-index.json`` for each question's taxonomy and
``questions.jsonl`` for its body, and writes a flat JSON array that
``app.cli import`` understands. Nothing is downloaded here.

The bank holds two generations of math item. Current ("digital") items carry
a ``stem``, an ``answerOptions`` list and a letter in ``correct_answer``;
older ("legacy", keyed by ``ibn``) items carry a ``prompt`` and an ``answer``
object whose choices are lettered a-d. Both end up in the same shape.

Formulas become LaTeX (see ``mathml.py``), figures are lifted out into the
``image`` field, and tables stay inline in the prompt with the class the
frontend styles.

A Reading and Writing item is a passage (``stimulus``) and a question about
it, both written in HTML — underlined sentences, blanks to fill, poems, paired
texts, the odd table or chart. That markup is kept, trimmed to the tags the
frontend styles, and the passage travels in the ``passage`` field.

    python3 tools/to_bank.py -o math-questions.json
    python3 tools/to_bank.py --test reading -o reading-questions.json
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterator

sys.path.insert(0, str(Path(__file__).resolve().parent))

import mathml
from paths import INDEX, QUESTIONS

#: The bank's one-letter difficulty, per assessment, in this project's words.
DIFFICULTY = {"E": "Easy", "M": "Medium", "H": "Hard"}

#: Skill names as this project spells them, keyed by the bank's spelling
#: lower-cased and stripped — the bank leaves a trailing space on a few.
SKILLS = (
    "Linear equations in one variable",
    "Linear equations in two variables",
    "Linear functions",
    "Systems of two linear equations in two variables",
    "Linear inequalities in one or two variables",
    "Equivalent expressions",
    "Nonlinear equations in one variable and systems of equations in two variables",
    "Nonlinear functions",
    "Ratios, rates, proportional relationships, and units",
    "Percentages",
    "One-variable data: distributions and measures of center and spread",
    "Two-variable data: models and scatterplots",
    "Probability and conditional probability",
    "Inference from sample statistics and margin of error",
    "Evaluating statistical claims: observational studies and experiments",
    "Area and volume",
    "Lines, angles, and triangles",
    "Right triangles and trigonometry",
    "Circles",
)
BY_SKILL = {skill.lower(): skill for skill in SKILLS}

READING_SKILLS = (
    "Words in Context",
    "Text Structure and Purpose",
    "Cross-Text Connections",
    "Central Ideas and Details",
    "Command of Evidence",
    "Inferences",
    "Rhetorical Synthesis",
    "Transitions",
    "Boundaries",
    "Form, Structure, and Sense",
)
BY_READING_SKILL = {skill.lower(): skill for skill in READING_SKILLS}

DOMAINS = {
    "algebra": "Algebra",
    "advanced math": "Advanced Math",
    "problem-solving and data analysis": "Problem-Solving and Data Analysis",
    "geometry and trigonometry": "Geometry and Trigonometry",
}

READING_DOMAINS = {
    "craft and structure": "Craft and Structure",
    "information and ideas": "Information and Ideas",
    "expression of ideas": "Expression of Ideas",
    "standard english conventions": "Standard English Conventions",
}

#: The bank's name for each section, as ``questions-index.json`` records it.
TESTS = {"math": "Math", "reading": "R&W"}

OPTION_LETTERS = ("A", "B", "C", "D")

_TAG = re.compile(r"<[^>]+>")
_ITALIC = re.compile(r'<span[^>]*class="[^"]*italic[^"]*"[^>]*>(.*?)</span>', re.S | re.I)
_MATH_IMG = re.compile(r'<img[^>]*class="[^"]*math-img[^"]*"[^>]*>', re.S | re.I)
_ALT = re.compile(r'alt="([^"]*)"')
_BLOCK_END = re.compile(r"</(?:p|div|tr|li|h[1-6])>", re.I)
_BREAK = re.compile(r"<br\s*/?>", re.I)
_IMG = re.compile(r"<img\b[^>]*>", re.I)
#: Legacy rationales open with "Choice B is correct." when the item itself
#: forgot to record which choice that was.
_CHOICE_IN_RATIONALE = re.compile(r"\bChoice\s+([A-D])\b[^.]{0,40}\bis correct", re.I)

#: Verbal fractions the bank writes out in an image's alt text.
WORDED = {
    "one half": "1/2", "three halves": "3/2", "five halves": "5/2", "seven halves": "7/2",
    "one third": "1/3", "two thirds": "2/3", "four thirds": "4/3", "five thirds": "5/3",
    "one quarter": "1/4", "one fourth": "1/4", "three quarters": "3/4", "three fourths": "3/4",
    "one fifth": "1/5", "two fifths": "2/5", "three fifths": "3/5", "four fifths": "4/5",
    "one sixth": "1/6", "five sixths": "5/6", "one eighth": "1/8", "three eighths": "3/8",
    "one ninth": "1/9", "one tenth": "1/10",
}

_NUMBER = r"\d[\d,]*(?:\.\d+)?(?:\s*/\s*\d+)?"
_WORDS = "|".join(sorted((re.escape(word) for word in WORDED), key=len, reverse=True))
#: "The correct answer is <value>." Only a value sitting immediately after that
#: phrase is trusted — anything further into the rationale is as likely to be a
#: step of the working as the answer. The terminator has to let a decimal point
#: through while still stopping at the end of the sentence.
_ANSWER_IN_RATIONALE = re.compile(
    r"correct answer is\s*(?:<span[^>]*>\s*)?"
    r"(?:<img\b[^>]*\balt=\"([^\"]*)\"[^>]*>"
    rf"|(negative\s+|-)?({_NUMBER}|{_WORDS})"
    r")"
    r"\s*(?:\.(?:\s|$)|[<,;]|$)",
    re.I,
)
_OVER = re.compile(r"^(\d+)\s+over\s+(\d+)$", re.I)


class Skipped(Exception):
    """Raised when a question cannot be represented in this project's format."""


# -- pulling structure out of a body ---------------------------------------


def extract_blocks(markup: str, tag: str) -> tuple[str, list[str]]:
    """Cut every balanced ``<tag>…</tag>`` out of ``markup``.

    Nesting matters — a ``<g>`` inside an ``<svg>``, a ``<table>`` inside a
    ``<figure>`` — so this counts depth rather than matching the first close
    tag the way a plain regex would.
    """
    opener = re.compile(rf"<{tag}\b", re.I)
    token = re.compile(rf"<(/?){tag}\b[^>]*?(/?)>", re.I)

    blocks: list[str] = []
    out: list[str] = []
    position = 0

    while True:
        start = opener.search(markup, position)
        if not start:
            out.append(markup[position:])
            return "".join(out), blocks

        out.append(markup[position : start.start()])
        depth = 0
        cursor = start.start()
        for match in token.finditer(markup, start.start()):
            if match.group(2):  # self-closing, e.g. <svg .../>
                if depth == 0:
                    cursor = match.end()
                    break
                continue
            depth += -1 if match.group(1) else 1
            if depth == 0:
                cursor = match.end()
                break
        else:  # unbalanced; take the rest and stop looking
            cursor = len(markup)

        blocks.append(markup[start.start() : cursor])
        position = cursor


def _with_formulas(markup: str, render):
    """Run ``render`` over ``markup`` with its formulas held aside as placeholders.

    Both callers need this: a literal "$" left in the prose would pair with a
    real formula's delimiter and set everything between the two as maths, so it
    has to be escaped — but only once the formulas are out of the way.
    """
    formulas: list[str] = []

    def hold(latex: str) -> str:
        latex = latex.strip()
        if not latex:
            return ""
        formulas.append(latex)
        return f"\x00{len(formulas) - 1}\x00"

    body = render(mathml._MATH.sub(lambda m: hold(mathml.to_latex(m.group(0))), markup), hold)
    body = body.replace("$", "$\\$$")
    return re.sub(r"\x00(\d+)\x00", lambda m: f"${formulas[int(m.group(1))]}$", body)


def to_text(markup: str, *, keep_math_images: bool) -> str:
    """Flatten a question body to the plain text plus LaTeX the app renders."""

    def render(text: str, hold) -> str:
        text = _ITALIC.sub(lambda m: hold(_italic(m.group(1))), text)
        if keep_math_images:
            # Legacy items draw their formulas as base64 PNGs. The alt text is
            # the verbal reading, which is all that survives the flattening.
            text = _MATH_IMG.sub(lambda m: f" {_alt_of(m.group(0))} ", text)
        else:
            text = _MATH_IMG.sub("", text)
        text = _BREAK.sub("\n", text)
        text = _BLOCK_END.sub("\n\n", text)
        text = _TAG.sub("", text)
        text = html.unescape(text)
        text = re.sub(r"[^\S\n]+", " ", text)
        return re.sub(r"\n{3,}", "\n\n", text)

    return _with_formulas(markup, render).strip()


def _italic(inner: str) -> str:
    """A ``<span class="italic">`` marks a variable — but only when it holds one.

    The bank sometimes leaves a span open across a table cell, so anything that
    is not a short run of plain text is passed through as prose instead of
    being set as maths.
    """
    body = html.unescape(_TAG.sub("", inner)).strip()
    if not body or len(body) > 24 or "\n" in body:
        return ""
    return body


def _normalise(value: str) -> str | None:
    """One stated answer as the app stores it, or None if it is not plainly one."""
    value = value.strip().rstrip(".").strip()
    lowered = value.lower()

    negative = False
    for prefix in ("negative ", "-"):
        if lowered.startswith(prefix):
            negative, lowered = True, lowered[len(prefix):].strip()
            break

    if lowered in WORDED:
        lowered = WORDED[lowered]
    else:
        over = _OVER.match(lowered)
        if over:
            lowered = f"{over.group(1)}/{over.group(2)}"

    lowered = lowered.replace(" ", "").replace(",", "")
    if not re.fullmatch(r"\d+(?:\.\d+)?(?:/\d+)?", lowered):
        return None
    return ("-" if negative else "") + lowered


def read_answer(rationale: str) -> str | None:
    """The answer a legacy rationale states outright, or None if it only works up to it.

    A mis-read key is worse than a missing question — the app would mark a
    right answer wrong — so anything that is not plainly a number or a fraction
    is left alone and the question is skipped.
    """
    match = _ANSWER_IN_RATIONALE.search(rationale)
    if not match:
        return None
    alt, sign, value = match.groups()
    if alt is not None:
        return _normalise(html.unescape(alt))
    return _normalise(f"{sign or ''}{value}")


def _alt_of(tag: str) -> str:
    match = _ALT.search(tag)
    return html.unescape(match.group(1)) if match else ""


def _figure(svgs: list[str], tables: list[str]) -> tuple[str | None, str]:
    """The question's image, and the table markup that stays in the prompt."""
    image = None
    if svgs:
        # A question with several drawings ships them side by side.
        image = "".join(_label_svg(svg) for svg in svgs)

    prefix = ""
    for table in tables:
        cleaned = _with_formulas(table, lambda body, hold: html.unescape(body))
        # The bank ships column widths and borders inline; the app's own
        # .question-table rules should decide how a table looks here.
        cleaned = cleaned.replace("&", "&amp;")
        cleaned = re.sub(r'\s(?:class|style|border|cellpadding|cellspacing|width)="[^"]*"', "", cleaned)
        cleaned = re.sub(r"</?figure[^>]*>", "", cleaned)
        cleaned = cleaned.replace("<table", '<table class="question-table"', 1)
        prefix += cleaned.strip() + "\n"
    return image, prefix


def _label_svg(svg: str) -> str:
    """A lifted figure still has to announce itself to a screen reader."""
    if "role=" not in svg:
        svg = re.sub(r"<svg\b", '<svg role="img"', svg, count=1)
    return svg


# -- one question ----------------------------------------------------------


def convert(record: dict, entry: dict, *, keep_math_images: bool) -> dict[str, Any]:
    """Map one downloaded question onto this project's fields."""
    domain = DOMAINS.get((entry.get("domain") or "").strip().lower())
    skill = BY_SKILL.get((entry.get("skill") or "").strip().lower())
    if not domain or not skill:
        raise Skipped(f"unknown taxonomy {entry.get('domain')!r} / {entry.get('skill')!r}")

    difficulty = DIFFICULTY.get((entry.get("difficulty") or {}).get("SAT") or "")
    if not difficulty:
        raise Skipped("no SAT difficulty")

    body, options, accepted, qtype = _parts(record)

    body, svgs = extract_blocks(body, "svg")
    body, figures = extract_blocks(body, "figure")
    body, tables = extract_blocks(body, "table")
    for figure in figures:
        inner, inner_tables = extract_blocks(figure, "table")
        tables.extend(inner_tables)
        _, inner_svgs = extract_blocks(inner, "svg")
        svgs.extend(inner_svgs)

    image, table_markup = _figure(svgs, tables)
    text = (table_markup + to_text(body, keep_math_images=keep_math_images)).strip()
    if not text:
        raise Skipped("empty prompt")

    question: dict[str, Any] = {
        "question_id": entry["id"],
        "domain": domain,
        "skill": skill,
        "difficulty": difficulty,
        "type": qtype,
        "text": text,
        "answer": accepted[0],
        "rationale": to_text(record.get("rationale") or "", keep_math_images=keep_math_images),
        "image": image,
        "source": "College Board SAT Suite Educator Question Bank",
    }
    if qtype == "MCQ":
        question["options"] = options
    if len(accepted) > 1:
        # The app scores against `answer` plus these.
        question["accepted_answers"] = accepted[1:]
    return question


def _parts(record: dict) -> tuple[str, list[str], list[str], str]:
    """``(body, options, accepted answers, type)`` for either generation of item."""
    if record.get("stem") is not None:
        return _digital(record)
    return _legacy(record)


def _digital(record: dict) -> tuple[str, list[str], str, str]:
    body = record.get("stem") or ""
    correct = record.get("correct_answer") or record.get("keys") or []
    if not correct:
        raise Skipped("no answer")
    first = str(correct[0]).strip()

    if (record.get("type") or "").lower() == "spr":
        # A grid-in often has several acceptable forms — the bank lists them,
        # e.g. ["0.25", "1/4"] — and every one of them has to be accepted.
        return body, [], [str(value).strip() for value in correct if str(value).strip()], "SPR"

    choices = record.get("answerOptions") or []
    if len(choices) != len(OPTION_LETTERS):
        raise Skipped(f"{len(choices)} options")

    options = [
        f"{letter}) {_option_text(choice.get('content') or '')}"
        for letter, choice in zip(OPTION_LETTERS, choices)
    ]
    letter = first.upper()
    if letter not in OPTION_LETTERS:
        raise Skipped(f"answer {first!r} is not an option letter")
    return body, options, [letter], "MCQ"


def _legacy(record: dict) -> tuple[str, list[str], str, str]:
    body = (record.get("prompt") or "") + (record.get("body") or "")
    answer = record.get("answer") or {}
    choices = answer.get("choices") or {}
    rationale = answer.get("rationale") or ""
    correct = str(answer.get("correct_choice") or "").strip()

    if not choices:
        value = str(answer.get("correct_answer") or "").strip() or read_answer(rationale)
        if not value:
            raise Skipped("answer only stated inside the working")
        return body, [], [value], "SPR"

    ordered = sorted(choices)
    if len(ordered) != len(OPTION_LETTERS):
        raise Skipped(f"{len(ordered)} options")
    if correct not in choices:
        # The item forgot to record the key; its rationale still names it.
        named = _CHOICE_IN_RATIONALE.search(rationale)
        if not named:
            raise Skipped("no answer")
        correct = ordered[OPTION_LETTERS.index(named.group(1).upper())]

    options = [
        f"{letter}) {_option_text(choices[key].get('body') or '')}"
        for letter, key in zip(OPTION_LETTERS, ordered)
    ]
    return body, options, [OPTION_LETTERS[ordered.index(correct)]], "MCQ"


def _option_text(markup: str) -> str:
    """One answer choice, flattened to a single line."""
    stripped, _ = extract_blocks(markup, "svg")
    body = to_text(stripped, keep_math_images=True)
    # A choice can be two paragraphs — the two equations of a system, say —
    # and those have to stay apart once the option is one line.
    lines = [" ".join(line.split()) for line in body.splitlines()]
    body = "; ".join(line for line in lines if line)
    if body:
        return body

    # Some legacy items offer four graphs to choose between. The choice is the
    # picture, so it travels as markup; the frontend renders an option's body
    # as HTML, and the bank's own alt text keeps it readable without images.
    pictures = _IMG.findall(markup)
    if pictures:
        return "".join(_label_svg(picture) for picture in pictures)
    raise Skipped("empty option")


# -- Reading and Writing ---------------------------------------------------

_TAG = re.compile(r"<(/?)([A-Za-z][\w-]*)([^>]*?)(/?)>")
_ATTR = re.compile(r'([\w-]+)\s*=\s*"([^"]*)"')
_VOID_TAGS = {"br", "img", "hr", "wbr"}
#: Tags kept as they are, apart from their attributes.
_KEPT_TAGS = {
    "p", "em", "strong", "u", "sup", "sub", "ul", "ol", "li", "br", "blockquote",
    "table", "caption", "thead", "tbody", "tfoot", "tr", "th", "td",
}
_KEPT_ATTRIBUTES = {"lang", "scope", "colspan", "rowspan"}
_EMPTY_PARAGRAPH = re.compile(r"<p(?: class=\"[^\"]*\")?>(?:\s|&nbsp;)*</p>")
_BLOCK_IN_PARAGRAPH = re.compile(
    r"<p(?: class=\"[^\"]*\")?>\s*(<(?:table|ul|ol|blockquote)\b.*?</(?:table|ul|ol|blockquote)>)\s*</p>",
    re.S,
)


def _class_for(tag: str, attributes: dict[str, str]) -> str | None:
    """The frontend's class for the bank's inline styling, if it has one."""
    classes = attributes.get("class", "")
    style = attributes.get("style", "").replace(" ", "")
    if tag == "table":
        return "question-table"
    if "dap_poemexcerpt" in classes:
        return "passage-poem"
    if "dap_copyright" in classes:
        return "passage-note"
    if "padding-left" in style:
        return "passage-indent"
    if "text-align:right" in style:
        return "passage-right"
    if "text-align:center" in style and tag != "th" and tag != "td":
        return "passage-center"
    return None


def _open_tag(tag: str, attributes: dict[str, str], extra_class: str | None) -> str:
    kept = {name: value for name, value in attributes.items() if name in _KEPT_ATTRIBUTES}
    if extra_class:
        kept["class"] = extra_class
    rendered = "".join(f' {name}="{html.escape(value, quote=True)}"' for name, value in kept.items())
    return f"<{tag}{rendered}>"


def clean_reading_markup(markup: str) -> str:
    """Trim a passage, stem, option or rationale to the markup the frontend styles.

    Screen-reader-only spans go (the visible text says the same), wrappers
    that only carried accessibility or styling attributes are unwrapped, an
    underlined span becomes ``<u>``, and the few inline styles the bank uses
    — an indented paragraph, a right-aligned credit, a poem — become classes.
    Nesting is honoured, so an underlined sentence with an italic word inside
    it comes out whole.
    """
    out: list[str] = []
    #: What to do when each open tag closes: emit a close tag, or nothing.
    stack: list[tuple[str, str]] = []
    position = 0
    dropping = 0

    for match in _TAG.finditer(markup):
        text = markup[position : match.start()]
        position = match.end()
        if not dropping:
            out.append(text)

        closing, tag, raw_attributes, self_closing = match.groups()
        tag = tag.lower()

        if closing:
            if dropping:
                dropping -= 1
                continue
            while stack:
                opened, close = stack.pop()
                if close:
                    out.append(close)
                if opened == tag:
                    break
            continue

        if dropping:
            if tag not in _VOID_TAGS and not self_closing:
                dropping += 1
            continue

        attributes = {name.lower(): value for name, value in _ATTR.findall(raw_attributes)}
        if "sr-only" in attributes.get("class", ""):
            # Screen-reader text: the visible passage says the same, and a
            # chart's long description would give the answer away in print.
            dropping = 1
            continue
        if tag in _VOID_TAGS or self_closing:
            if tag in _KEPT_TAGS:
                out.append(f"<{tag}>")
            continue

        if tag == "span" and "underline" in attributes.get("style", ""):
            out.append("<u>")
            stack.append((tag, "</u>"))
        elif tag == "span" and "dap_copyright" in attributes.get("class", ""):
            out.append('<span class="passage-note">')
            stack.append((tag, "</span>"))
        elif tag == "span" and attributes.get("lang"):
            out.append(_open_tag(tag, attributes, None))
            stack.append((tag, "</span>"))
        elif tag in _KEPT_TAGS:
            out.append(_open_tag(tag, attributes, _class_for(tag, attributes)))
            stack.append((tag, f"</{tag}>"))
        else:
            # figure, div, span, and anything else: the content stays, the box goes.
            stack.append((tag, ""))

    if not dropping:
        out.append(markup[position:])
    while stack:
        _, close = stack.pop()
        if close:
            out.append(close)

    cleaned = re.sub(r"\s+", " ", "".join(out))
    # A block inside a paragraph is not HTML a browser keeps together; the
    # bank wraps its tables and lists that way, so the paragraph goes.
    cleaned = _BLOCK_IN_PARAGRAPH.sub(r"\1", cleaned)
    cleaned = _EMPTY_PARAGRAPH.sub("", cleaned)
    return cleaned.strip()


def _inline(markup: str) -> str:
    """Markup as one run of inline text: paragraphs joined, the outer ``<p>`` gone."""
    cleaned = clean_reading_markup(markup)
    parts = [part.strip() for part in re.split(r"</?p(?: [^>]*)?>", cleaned)]
    return " ".join(part for part in parts if part).strip()


def convert_reading(record: dict, entry: dict) -> dict[str, Any]:
    """Map one Reading and Writing item onto this project's fields."""
    domain = READING_DOMAINS.get((entry.get("domain") or "").strip().lower())
    skill = BY_READING_SKILL.get((entry.get("skill") or "").strip().lower())
    if not domain or not skill:
        raise Skipped(f"unknown taxonomy {entry.get('domain')!r} / {entry.get('skill')!r}")

    difficulty = DIFFICULTY.get((entry.get("difficulty") or {}).get("SAT") or "")
    if not difficulty:
        raise Skipped("no SAT difficulty")
    if record.get("stem") is None:
        raise Skipped("legacy item")

    stimulus = record.get("stimulus") or ""
    stimulus, svgs = extract_blocks(stimulus, "svg")
    passage = clean_reading_markup(stimulus)
    text = _inline(record.get("stem") or "")
    if not text:
        raise Skipped("empty prompt")

    correct = record.get("correct_answer") or []
    letter = str(correct[0]).strip().upper() if correct else ""
    choices = record.get("answerOptions") or []
    if len(choices) != len(OPTION_LETTERS):
        raise Skipped(f"{len(choices)} options")
    if letter not in OPTION_LETTERS:
        raise Skipped(f"answer {letter!r} is not an option letter")
    options = []
    for option_letter, choice in zip(OPTION_LETTERS, choices):
        body = _inline(choice.get("content") or "")
        if not body:
            raise Skipped("empty option")
        options.append(f"{option_letter}) {body}")

    return {
        "question_id": entry["id"],
        "domain": domain,
        "skill": skill,
        "difficulty": difficulty,
        "type": "MCQ",
        "passage": passage,
        "text": text,
        "options": options,
        "answer": letter,
        "rationale": clean_reading_markup(record.get("rationale") or ""),
        "image": "".join(_label_svg(svg) for svg in svgs) or None,
        "source": "College Board SAT Suite Educator Question Bank",
    }


# -- driving ---------------------------------------------------------------


def load_bodies() -> Iterator[dict]:
    for line in QUESTIONS.open(encoding="utf-8"):
        line = line.strip()
        if line:
            yield json.loads(line)


def build(*, keep_math_images: bool, legacy: bool, test: str = "math") -> tuple[list[dict], Counter]:
    index = {q["id"]: q for q in json.loads(INDEX.read_text())["questions"]}
    questions: list[dict] = []
    reasons: Counter[str] = Counter()

    for record in load_bodies():
        entry = index.get(record.get("_key"))
        if not entry or entry.get("test") != TESTS[test]:
            continue
        if "SAT" not in (entry.get("assessments") or []):
            reasons["not on the SAT"] += 1
            continue
        if entry.get("legacy") and not legacy:
            reasons["legacy item"] += 1
            continue
        try:
            if test == "reading":
                questions.append(convert_reading(record, entry))
            else:
                questions.append(convert(record, entry, keep_math_images=keep_math_images))
        except Skipped as reason:
            reasons[str(reason)] += 1

    return questions, reasons


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "-o", "--output", type=Path, default=None,
        help="where to write (default: math-questions.json or reading-questions.json)",
    )
    parser.add_argument(
        "--test", choices=tuple(TESTS), default="math",
        help="which section to convert (default: math)",
    )
    parser.add_argument(
        "--no-legacy",
        action="store_true",
        help="skip the older ibn-keyed items, whose formulas are bitmap images",
    )
    parser.add_argument(
        "--drop-math-images",
        action="store_true",
        help="drop a legacy item's bitmap formulas instead of keeping their verbal alt text",
    )
    args = parser.parse_args(argv)

    output = args.output or Path(f"{args.test}-questions.json")
    questions, reasons = build(
        keep_math_images=not args.drop_math_images, legacy=not args.no_legacy, test=args.test
    )
    output.write_text(json.dumps(questions, indent=1, ensure_ascii=False), encoding="utf-8")

    print(f"{len(questions)} {args.test} questions -> {output}")
    by_type = Counter(q["type"] for q in questions)
    by_difficulty = Counter(q["difficulty"] for q in questions)
    with_figure = sum(1 for q in questions if q["image"] or "<table" in q["text"])
    print(f"  type        {dict(by_type)}")
    print(f"  difficulty  {dict(by_difficulty)}")
    print(f"  with figure {with_figure}")
    for skill, count in Counter(q["skill"] for q in questions).most_common():
        print(f"    {count:>4}  {skill}")
    if reasons:
        print("  skipped:")
        for reason, count in reasons.most_common():
            print(f"    {count:>4}  {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
