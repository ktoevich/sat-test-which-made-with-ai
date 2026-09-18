"""Turn the bank's presentation MathML into the LaTeX that KaTeX renders.

Every formula in a question body arrives as a ``<math>`` element. The bank also
puts a verbal reading in its ``alttext`` ("StartFraction 12 x plus 28 Over 4
EndFraction"), which is what a screen reader gets; it is unusable as a printed
formula, so the markup itself is converted instead.

Only the presentation subset the bank actually uses is handled — see
``tools/README`` for the survey — and anything unrecognised falls back to its
text content rather than being dropped.
"""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ElementTree

#: Operators that need a LaTeX command or an escape. Anything not listed is
#: passed through as-is, which is right for + - = ( ) , . and friends.
OPERATORS = {
    "\u2212": "-",          # minus sign, as opposed to hyphen
    "\u00b7": "\\cdot",
    "\u22c5": "\\cdot",
    "\u00d7": "\\times",
    "\u00f7": "\\div",
    "\u2264": "\\le",
    "\u2265": "\\ge",
    "\u2260": "\\ne",
    "\u00b1": "\\pm",
    "\u2248": "\\approx",
    "\u221e": "\\infty",
    "\u2220": "\\angle",
    "\u25b3": "\\triangle",
    "\u2225": "\\parallel",
    "\u22a5": "\\perp",
    "\u2245": "\\cong",
    "\u223c": "\\sim",
    "\u00b0": "^\\circ",
    "\u03c0": "\\pi",
    "\u2192": "\\to",
    "\u21d2": "\\Rightarrow",
    "%": "\\%",
    "$": "\\$",
    "&": "\\&",
    "_": "\\_",
    "#": "\\#",
    "\u00a0": "\\,",
    "\u200a": "\\,",
    "\u2009": "\\,",
}

#: Multi-letter identifiers that are functions rather than a product of letters.
FUNCTIONS = {
    "sin", "cos", "tan", "sec", "csc", "cot", "log", "ln", "exp",
    "arcsin", "arccos", "arctan", "max", "min",
}

#: Characters that reach a formula from prose and have no maths meaning.
SUBSTITUTES = {
    "\u2062": "",          # invisible times
    "\u2061": "",          # function application
    "\u200b": "",
    "\u2206": "\\Delta",
    "\u0394": "\\Delta",
    "\U0001d4c1": "\\ell",
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2013": "-",
    "\u2014": "-",
}

#: Named constants written as a word.
CONSTANTS = {"\u03c0": "\\pi", "pi": "\\pi", "theta": "\\theta", "psi": "\\psi"}

_MATH = re.compile(r"<math\b.*?</math>", re.S | re.I)
#: The five entities XML defines itself; everything else has to become a
#: character before ElementTree will accept the fragment.
_KEEP = ("&lt;", "&gt;", "&amp;", "&quot;", "&apos;")
_ENTITY = re.compile(r"&(?:[a-zA-Z][a-zA-Z0-9]*|#\d+|#[xX][0-9a-fA-F]+);")


#: Every control word this module emits. A command butted up against a letter
#: has to be separated from it, and matching the exact set avoids the regex
#: backtracking into a shorter one — "\\text{" must not become "\\tex t{".
COMMANDS = sorted(
    {value.lstrip("^") for value in (*OPERATORS.values(), *SUBSTITUTES.values(), *CONSTANTS.values())
     if value.startswith(("\\", "^\\"))}
    | {f"\\{name}" for name in FUNCTIONS}
    | {"\\frac", "\\sqrt", "\\left", "\\right", "\\overline", "\\overrightarrow",
       "\\overset", "\\underset", "\\text", "\\begin", "\\end", "\\backslash"},
    key=len,
    reverse=True,
)
COMMAND_SET = frozenset(COMMANDS)
_CONTROL_WORD = re.compile(r"\\[a-zA-Z]+")


def _space_commands(latex: str) -> str:
    """Separate a control word from the letters that follow it.

    The whole run of letters after a backslash has to be considered at once:
    matching an alternation would let the regex back off from ``\\left`` to
    ``\\le`` and split a perfectly good command down the middle.
    """

    def fix(match: re.Match) -> str:
        run = match.group(0)
        for end in range(len(run), 1, -1):
            if run[:end] in COMMAND_SET:
                return run if end == len(run) else f"{run[:end]} {run[end:]}"
        return run

    return _CONTROL_WORD.sub(fix, latex)


def _resolve_entities(fragment: str) -> str:
    """Replace every entity except XML's own five with the character it means."""

    def swap(match: re.Match) -> str:
        text = match.group(0)
        if text in _KEEP:
            return text
        resolved = html.unescape(text)
        return resolved if resolved != text else ""

    return _ENTITY.sub(swap, fragment)


def _strip_namespace(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _text(node: ElementTree.Element) -> str:
    return "".join(node.itertext()).strip()


def _identifier(body: str) -> str:
    body = body.strip()
    if not body:
        return ""
    if body in CONSTANTS:
        return CONSTANTS[body]
    if body.lower() in FUNCTIONS:
        return f"\\{body.lower()}"
    if len(body) == 1:
        return OPERATORS.get(body, body)
    # A word like "cm" or "radians" is a unit, not a product of variables.
    return f"\\text{{{body}}}"


def _operator(body: str) -> str:
    body = body.strip() or " "
    return OPERATORS.get(body, body)


def _children(node: ElementTree.Element) -> list[ElementTree.Element]:
    return [child for child in node if _strip_namespace(child.tag) != "mspace"]


def _convert(node: ElementTree.Element) -> str:
    tag = _strip_namespace(node.tag)
    kids = _children(node)

    if tag in ("math", "mrow", "mstyle", "semantics", "mpadded"):
        return "".join(_convert(child) for child in kids) or _escape_text(node.text)
    if tag == "mn":
        return (node.text or "").strip()
    if tag == "mi":
        return _identifier(node.text or "")
    if tag == "mo":
        return _operator(node.text or "")
    if tag == "mtext":
        body = _text_escape((node.text or "").strip())
        return f"\\text{{{body}}}" if body else ""
    if tag == "mfrac" and len(kids) == 2:
        return f"\\frac{{{_convert(kids[0])}}}{{{_convert(kids[1])}}}"
    if tag == "msup" and len(kids) == 2:
        return f"{_wrap(_convert(kids[0]), kids[0])}^{{{_convert(kids[1])}}}"
    if tag == "msub" and len(kids) == 2:
        return f"{_wrap(_convert(kids[0]), kids[0])}_{{{_convert(kids[1])}}}"
    if tag == "msubsup" and len(kids) == 3:
        base = _wrap(_convert(kids[0]), kids[0])
        return f"{base}_{{{_convert(kids[1])}}}^{{{_convert(kids[2])}}}"
    if tag == "msqrt":
        return f"\\sqrt{{{''.join(_convert(child) for child in kids)}}}"
    if tag == "mroot" and len(kids) == 2:
        return f"\\sqrt[{_convert(kids[1])}]{{{_convert(kids[0])}}}"
    if tag == "mfenced":
        return _fenced(node, kids)
    if tag == "mover" and len(kids) == 2:
        accent = _text(kids[1])
        inner = _convert(kids[0])
        if accent in ("\u00af", "\u0304", "\u2015"):
            return f"\\overline{{{inner}}}"
        if accent == "\u2192":
            return f"\\overrightarrow{{{inner}}}"
        return f"\\overset{{{_convert(kids[1])}}}{{{inner}}}"
    if tag == "munder" and len(kids) == 2:
        return f"\\underset{{{_convert(kids[1])}}}{{{_convert(kids[0])}}}"
    if tag == "menclose":
        notation = node.get("notation", "")
        inner = "".join(_convert(child) for child in kids)
        return f"\\overline{{{inner}}}" if "top" in notation else inner
    if tag in ("mtable", "mtr", "mtd"):
        return _table(node, tag, kids)

    return "".join(_convert(child) for child in kids) or _escape_text(node.text)


def _table(node: ElementTree.Element, tag: str, kids: list[ElementTree.Element]) -> str:
    if tag == "mtd":
        return "".join(_convert(child) for child in kids)
    if tag == "mtr":
        return " & ".join(_convert(child) for child in kids)
    rows = " \\\\ ".join(_convert(child) for child in kids)
    return f"\\begin{{matrix}} {rows} \\end{{matrix}}"


def _fenced(node: ElementTree.Element, kids: list[ElementTree.Element]) -> str:
    left = node.get("open", "(") or "."
    right = node.get("close", ")") or "."
    separators = (node.get("separators") or ",").replace(" ", "")

    parts = [_convert(child) for child in kids]
    body = parts[0] if parts else ""
    for index, part in enumerate(parts[1:]):
        separator = separators[min(index, len(separators) - 1)] if separators else ","
        body += f"{separator} {part}"

    return f"\\left{_delimiter(left)} {body} \\right{_delimiter(right)}"


def _delimiter(char: str) -> str:
    if char in ("{", "}"):
        return f"\\{char}"
    if char == "|":
        return "|"
    return char or "."


def _wrap(latex: str, node: ElementTree.Element) -> str:
    """Parenthesise a base that is more than one token, so ``x+1`` squares right."""
    if len(latex) <= 1 or latex.startswith("\\left") or _strip_namespace(node.tag) == "mfenced":
        return latex
    if re.fullmatch(r"\\?[A-Za-z]+|\d+", latex):
        return latex
    return f"{{{latex}}}"


def _text_escape(body: str) -> str:
    """Escape prose so it survives being wrapped in ``\\text{…}``."""
    for char, replacement in (("\\", "\\backslash "), ("{", "\\{"), ("}", "\\}")):
        body = body.replace(char, replacement)
    for char in "%$&#_":
        body = body.replace(char, "\\" + char)
    return body


def _escape_text(text: str | None) -> str:
    body = (text or "").strip()
    return "".join(OPERATORS.get(char, char) for char in body)


def to_latex(fragment: str) -> str:
    """Convert one ``<math>…</math>`` fragment to a LaTeX body (no delimiters)."""
    try:
        root = ElementTree.fromstring(_resolve_entities(fragment))
    except ElementTree.ParseError:
        # Fall back to the verbal reading rather than losing the formula.
        alt = re.search(r'alttext="([^"]*)"', fragment)
        return html.unescape(alt.group(1)) if alt else ""

    latex = _convert(root)
    for char, replacement in SUBSTITUTES.items():
        latex = latex.replace(char, replacement)
    latex = re.sub(r"\s+", " ", latex).strip()
    # "\pi" immediately followed by a letter would read as the command "\pir".
    latex = _space_commands(latex)
    return latex.strip()


def replace_all(markup: str) -> str:
    """Swap every ``<math>`` element in ``markup`` for ``$…$``."""

    def swap(match: re.Match) -> str:
        latex = to_latex(match.group(0))
        return f"${latex}$" if latex else ""

    return _MATH.sub(swap, markup)
