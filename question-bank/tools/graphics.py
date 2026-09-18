"""Work out what visual a question carries, from the markup the bank returns.

Every figure in a question body is an inline ``<svg>`` whose ``aria-label``
names it in a fixed house style -- "Bar graph titled Maize Exports. The
horizontal axis is labeled Year. ..." -- and each one is paired with a "Long
description for ..." block holding the same information as prose. That label is
what we classify on: no image decoding involved, and the wording is the College
Board's own, so a question is only called a graph when the bank says it is.

Tables are separate: they come through as ``<figure class="table">`` and are
reported alongside the figures rather than counted as graphs.
"""

from __future__ import annotations

import html
import re

#: Question fields that can hold a body. Digital items use stem/stimulus;
#: legacy (ibn) items use prompt/body.
BODY_FIELDS = ("stem", "stimulus", "prompt", "body", "item_body")

_LABEL = re.compile(r'aria-label="([^"]*)"')
_TITLED = re.compile(r"\btitled\s+(.+?)(?:\.\s|\.$|$)", re.S)

#: Chart kinds, matched against the lowercased label. Order matters: the first
#: hit wins, so the specific names come before the generic "graph".
_CHARTS = (
    ("Scatterplot", ("scatterplot", "scatter plot")),
    ("Histogram", ("histogram",)),
    ("Dot plot", ("dotplot", "dot plot")),
    ("Box plot", ("boxplot", "box plot", "box-and-whisker")),
    ("Bar graph", ("bar graph", "bar chart")),
    ("Line graph", ("line graph", "line chart")),
    ("Circle graph", ("circle graph", "pie chart", "pie graph")),
)

#: Anything drawn on axes that is not one of the named chart types above.
_PLANE = ("xy-plane", "x y-plane", "coordinate plane", "coordinate grid")

_GEOMETRY = (
    "triangle", "circle", "rectangle", "square", "polygon", "angle", "parallelogram",
    "trapezoid", "rhombus", "cylinder", "cone", "sphere", "prism", "cube", "pyramid",
    "hexagon", "pentagon", "quadrilateral", "arc", "chord", "line segment", "vertex",
    "vertices", "perpendicular", "parallel lines", "diagram", "figure",
)

#: Kinds that count as a graph for the "does this topic have graphs" question.
GRAPH_KINDS = frozenset(
    [name for name, _ in _CHARTS] + ["Coordinate-plane graph", "Number line"]
)


def classify(label: str) -> str | None:
    """Name the kind of figure ``label`` describes, or None if it is not a figure.

    Returns None for the long-description twin of a figure (already counted via
    the figure itself) and for labels that mark up passage text rather than art.
    """
    text = html.unescape(label).strip()
    low = text.lower()
    if low.startswith("long description"):
        return None
    if low in ("referenced content", "") or low.startswith("passage"):
        return None
    for name, needles in _CHARTS:
        if any(n in low for n in needles):
            return name
    if any(n in low for n in _PLANE):
        return "Coordinate-plane graph"
    if "number line" in low:
        return "Number line"
    if re.search(r"\bgraphs?\b", low):
        return "Coordinate-plane graph"
    if "table" in low:
        return "Table"
    if any(n in low for n in _GEOMETRY):
        return "Geometric figure"
    return "Other figure"


def title_of(label: str) -> str | None:
    """The chart's own title, when its label carries one."""
    match = _TITLED.search(html.unescape(label))
    return match.group(1).strip() if match else None


def body_of(question: dict) -> str:
    return "\n".join(
        question[field] for field in BODY_FIELDS if isinstance(question.get(field), str)
    )


def describe(question: dict) -> dict:
    """Summarise the visuals in one fetched question."""
    body = body_of(question)
    figures = []
    for label in _LABEL.findall(body):
        kind = classify(label)
        if kind is None:
            continue
        figures.append({
            "kind": kind,
            "title": title_of(label),
            "label": html.unescape(label),
        })

    # An <svg> with no usable label is still a picture; say so rather than
    # quietly reporting the question as having none.
    if "<svg" in body and not figures:
        figures.append({"kind": "Other figure", "title": None, "label": None})

    kinds = sorted({f["kind"] for f in figures})
    return {
        "graph": any(k in GRAPH_KINDS for k in kinds),
        "kinds": kinds,
        "figures": figures,
        "table": '<figure class="table"' in body or "<table" in body,
    }
