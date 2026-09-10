"""Algebra templates: linear equations, systems, linear functions."""

from __future__ import annotations

import random

from fractions import Fraction

from .. import figures
from ..latex import fraction, linear, number, paren, sum_terms, tex, term
from .base import Question, Template, nonzero, numeric_variants, pick_distractors

DOMAIN = "Algebra"


def _line_alt(slope, intercept: int) -> str:
    """Prose description of a graphed line, for the export and screen readers."""
    step = abs(slope)
    direction = "rises" if slope > 0 else "falls"
    return (
        f"Coordinate-plane graph. A line is graphed in the xy-plane. It crosses the y-axis at "
        f"(0, {number(intercept)}) and {direction} {number(step)} unit"
        f"{'' if step == 1 else 's'} for every 1 unit to the right."
    )


class LinearEquationTemplate(Template):
    """Solve a linear equation in one variable."""

    key = "linear_equation"
    domain = DOMAIN
    skill = "Linear equations in one variable"
    types = ("MCQ", "SPR")

    def build(self, rng: random.Random, qtype: str, difficulty: str) -> Question:
        solution = nonzero(rng, -9, 12)

        if difficulty == "Easy":
            a, b = nonzero(rng, 2, 9), rng.randint(-15, 15)
            left, right = f"{linear(a, b)}", number(a * solution + b)
            move = f"Subtract {number(b)} from" if b >= 0 else f"Add {number(-b)} to"
            steps = (
                f"{move} both sides to get {tex(f'{term(a)} = {number(a * solution)}')}, "
                f"then divide by {number(a)}."
            )
        elif difficulty == "Medium":
            a, b = nonzero(rng, 2, 7), nonzero(rng, -8, 8)
            outer = nonzero(rng, 2, 5)
            left = f"{number(outer)}({linear(a, b)})"
            right = number(outer * (a * solution + b))
            steps = (
                f"Divide both sides by {number(outer)}, then solve {tex(f'{linear(a, b)} = {number(a * solution + b)}')}."
            )
        else:
            a, c = nonzero(rng, 3, 9), nonzero(rng, -8, -2)
            b = nonzero(rng, -12, 12)
            d = (a - c) * solution + b
            left, right = linear(a, b), linear(c, d)
            steps = (
                f"Collect the variable on one side: {tex(f'{term(a - c)} = {number(d - b)}')}, "
                f"then divide by {number(a - c)}."
            )

        equation = tex(f"{left} = {right}")
        answer = number(solution)
        rationale = f"{steps} The solution is {tex(f'x = {answer}')}."

        if qtype == "SPR":
            return self.spr(
                text=f"What value of {tex('x')} satisfies the equation {equation}?",
                answer=answer,
                rationale=rationale,
                difficulty=difficulty,
            )

        distractors = pick_distractors(
            answer,
            [number(-solution), number(solution + 1), number(solution - 1), number(solution * 2)],
            pad=numeric_variants(solution),
        )
        return self.mcq(
            text=f"What is the solution to the equation {equation}?",
            correct=answer,
            distractors=distractors,
            rationale=rationale,
            difficulty=difficulty,
            rng=rng,
        )


class LinearSystemTemplate(Template):
    """Solve a system of two linear equations in two variables."""

    key = "linear_system"
    domain = DOMAIN
    skill = "Systems of two linear equations in two variables"
    types = ("MCQ", "SPR")

    def build(self, rng: random.Random, qtype: str, difficulty: str) -> Question:
        x, y = nonzero(rng, -8, 9), nonzero(rng, -8, 9)
        bound = {"Easy": 4, "Medium": 7, "Hard": 11}[difficulty]

        a, b = nonzero(rng, 1, bound), nonzero(rng, 1, bound)
        c, d = nonzero(rng, -bound, bound), nonzero(rng, -bound, bound)
        while a * d - b * c == 0:
            d = nonzero(rng, -bound, bound)

        first = f"{sum_terms(term(a), term(b, 'y'))} = {number(a * x + b * y)}"
        second = f"{sum_terms(term(c), term(d, 'y'))} = {number(c * x + d * y)}"
        system = f"$$\\begin{{cases}} {first} \\\\ {second} \\end{{cases}}$$"

        asks_sum = difficulty == "Hard"
        target = x + y if asks_sum else x
        answer = number(target)
        label = tex("x + y") if asks_sum else tex("x")
        rationale = (
            f"Solving the system gives {tex(f'x = {number(x)}')} and {tex(f'y = {number(y)}')}, "
            f"so {label} is {tex(answer)}."
        )

        text = f"{system}\nFor the solution {tex('(x, y)')} of the system above, what is the value of {label}?"

        if qtype == "SPR":
            return self.spr(text=text, answer=answer, rationale=rationale, difficulty=difficulty)

        distractors = pick_distractors(
            answer,
            [number(y), number(x - y), number(-target), number(target + 2), number(target - 3)],
            pad=numeric_variants(target),
        )
        return self.mcq(
            text=text,
            correct=answer,
            distractors=distractors,
            rationale=rationale,
            difficulty=difficulty,
            rng=rng,
        )


class SlopeTemplate(Template):
    """Find the slope of the line through two points."""

    key = "slope_from_points"
    domain = DOMAIN
    skill = "Linear functions"
    types = ("MCQ",)

    def build(self, rng: random.Random, qtype: str, difficulty: str) -> Question:
        x1, y1 = rng.randint(-8, 8), rng.randint(-8, 8)
        run = nonzero(rng, 1, 6) if difficulty == "Easy" else nonzero(rng, -6, 6)
        rise = nonzero(rng, -9, 9)
        if difficulty == "Easy":
            rise = run * nonzero(rng, -4, 4)

        x2, y2 = x1 + run, y1 + rise
        answer = tex(fraction(rise, run))
        rationale = (
            f"Slope is {tex('\\frac{y_2 - y_1}{x_2 - x_1}')}, here "
            f"{tex(f'\\frac{{{number(y2)} - {paren(y1)}}}{{{number(x2)} - {paren(x1)}}}')} "
            f"= {answer}."
        )

        distractors = pick_distractors(
            answer,
            [
                tex(fraction(run, rise)),
                tex(fraction(-rise, run)),
                tex(fraction(rise + run, run)),
                tex(fraction(rise, run + 1) if run != -1 else fraction(rise, run - 1)),
            ],
            pad=(tex(fraction(rise + delta, run)) for delta in (1, -1, 2, -2, 3, -3, 5, -5)),
        )
        return self.mcq(
            text=(
                f"A line in the {tex('xy')}-plane passes through the points "
                f"{tex(f'({number(x1)}, {number(y1)})')} and {tex(f'({number(x2)}, {number(y2)})')}. "
                "What is the slope of the line?"
            ),
            correct=answer,
            distractors=distractors,
            rationale=rationale,
            difficulty=difficulty,
            rng=rng,
        )


class SlopeFromGraphTemplate(Template):
    """Read the slope or the ``y``-intercept off a line drawn on a grid.

    The blueprint's Linear functions row asks for exactly this — "simple
    graphs: find the slope or an intercept" — so the question ships the graph
    and the student reads the answer off it rather than off a pair of points.
    """

    key = "slope_from_graph"
    domain = DOMAIN
    skill = "Linear functions"
    types = ("MCQ", "SPR")

    GRID_END = 8

    def build(self, rng: random.Random, qtype: str, difficulty: str) -> Question:
        rise, run = self._gradient(rng, difficulty)
        intercept = rng.randint(-4, 4)
        slope = Fraction(rise, run)

        # The line runs edge to edge, the way a graphed line looks on the test.
        (x1, y1), (x2, y2) = figures.clip_line(slope, intercept, self.GRID_END)

        image = {
            "xEnd": self.GRID_END,
            "yEnd": self.GRID_END,
            "step": 2,
            "alt": _line_alt(slope, intercept),
            "draw": (
                f'<line x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}" '
                f'stroke="#2563eb" stroke-width="2"/>'
                f'<circle cx="0" cy="{intercept}" r="0.18" fill="#2563eb"/>'
            ),
        }

        # A grid-in cannot take a fraction bar drawn as LaTeX, so it only ever
        # asks for the intercept, which is always a whole number here.
        wants_slope = qtype != "SPR" and rng.choice([True, True, False])
        if wants_slope:
            answer = fraction(rise, run)
            question = "What is the slope of the line?"
            rationale = (
                f"Reading two lattice points off the line, {tex('y')} changes by "
                f"{number(rise)} for every {number(run)} of change in {tex('x')}, so the slope is "
                f"{tex(answer)}."
            )
            wrong = [
                fraction(run, rise),
                fraction(-rise, run),
                number(intercept),
                fraction(rise + run, run),
            ]
        else:
            answer = number(intercept)
            question = f"At what value of {tex('y')} does the line cross the {tex('y')}-axis?"
            rationale = (
                f"The line meets the {tex('y')}-axis at {tex(f'(0, {answer})')}, so the "
                f"{tex('y')}-intercept is {tex(answer)}."
            )
            wrong = [number(-intercept), fraction(rise, run), number(intercept + 1), number(intercept - 2)]

        text = f"The graph above shows a line in the {tex('xy')}-plane. {question}"
        if qtype == "SPR":
            return self.spr(
                text=text, answer=answer, rationale=rationale, difficulty=difficulty, image=image
            )

        return self.mcq(
            text=text,
            correct=tex(answer),
            distractors=[tex(value) for value in pick_distractors(answer, wrong, pad=numeric_variants(float(slope) if wants_slope else intercept))],
            rationale=rationale,
            difficulty=difficulty,
            rng=rng,
            image=image,
        )

    def _gradient(self, rng: random.Random, difficulty: str) -> tuple[int, int]:
        """Rise and run, kept readable off a grid ruled every 2 units."""
        if difficulty == "Hard":
            run = rng.choice([2, 3, 4])
            rise = nonzero(rng, -5, 5)
            while Fraction(rise, run).denominator == 1:
                rise = nonzero(rng, -5, 5)
            return rise, run
        if difficulty == "Medium":
            return nonzero(rng, -4, 4), 1
        return nonzero(rng, 1, 3), 1


class LineGraphTemplate(Template):
    """Read the equation of a line drawn on a coordinate grid."""

    key = "line_graph"
    domain = DOMAIN
    skill = "Linear equations in two variables"
    types = ("MCQ",)
    difficulties = ("Easy", "Medium")

    GRID_END = 8

    def build(self, rng: random.Random, qtype: str, difficulty: str) -> Question:
        slope = nonzero(rng, -3, 3)
        intercept = rng.randint(-4, 4)

        # Run the line out to the edge of the grid. Flooring a span to a whole
        # number instead would push a steep line off the grid, where the browser
        # silently clips it.
        (x1, y1), (x2, y2) = figures.clip_line(slope, intercept, self.GRID_END)

        equation = f"y = {linear(slope, intercept)}"
        answer = tex(equation)
        # A negative slope falls; saying it "rises -2" reads badly.
        direction = "rises" if slope > 0 else "falls"
        step = abs(slope)
        rationale = (
            f"The line crosses the {tex('y')}-axis at {tex(f'(0, {number(intercept)})')} and "
            f"{direction} {number(step)} unit{'' if step == 1 else 's'} for every 1 unit to the "
            f"right, so its equation is {answer}."
        )

        distractors = pick_distractors(
            answer,
            [
                tex(f"y = {linear(-slope, intercept)}"),
                tex(f"y = {linear(slope, -intercept)}") if intercept else tex(f"y = {linear(slope + 1, 1)}"),
                tex(f"y = {linear(intercept if intercept else 2, slope)}"),
                tex(f"y = {linear(slope + 1, intercept)}"),
            ],
            pad=(
                tex(f"y = {linear(slope + delta, intercept + offset)}")
                for delta, offset in ((2, 0), (-2, 0), (0, 1), (0, -1), (1, 1), (-1, -1))
            ),
        )

        image = {
            "xEnd": self.GRID_END,
            "yEnd": self.GRID_END,
            "step": 2,
            "alt": _line_alt(slope, intercept),
            "draw": (
                f'<line x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}" stroke="#2563eb" stroke-width="2"/>'
                f'<circle cx="0" cy="{intercept}" r="0.18" fill="#2563eb"/>'
            ),
        }

        return self.mcq(
            text="Which equation represents the line shown in the $xy$-plane above?",
            correct=answer,
            distractors=distractors,
            rationale=rationale,
            difficulty=difficulty,
            rng=rng,
            image=image,
        )


class TwoVariableModelTemplate(Template):
    """A situation modelled by ``ax + by = c``; find one quantity from the other.

    At Hard the second quantity is only given relative to the first, so the
    student has to substitute ``x = y + k`` before solving.
    """

    key = "two_variable_model"
    domain = DOMAIN
    skill = "Linear equations in two variables"
    types = ("MCQ", "SPR")
    difficulties = ("Medium", "Hard")

    #: (x item, y item, sentence introducing the two rates, what c counts)
    SCENARIOS = (
        ("posters", "flyers", "A print shop charges {a} dollars per poster and {b} dollars per flyer.", "cost {c} dollars"),
        ("adult tickets", "child tickets", "A theater sells adult tickets for {a} dollars each and child tickets for {b} dollars each.", "brought in {c} dollars"),
        ("large boxes", "small boxes", "A large box holds {a} books and a small box holds {b} books.", "holds {c} books in total"),
        ("hours of tutoring", "hours of babysitting", "Maya earns {a} dollars per hour of tutoring and {b} dollars per hour of babysitting.", "earned {c} dollars"),
    )

    def build(self, rng: random.Random, qtype: str, difficulty: str) -> Question:
        x_item, y_item, intro, outcome = rng.choice(self.SCENARIOS)
        a = rng.randint(2, 12)
        b = rng.randint(2, 12)
        while b == a:
            b = rng.randint(2, 12)
        y0 = rng.randint(2, 12)
        # At least 2, so "N more posters than flyers" never needs a singular.
        extra = rng.randint(2, 6)
        x0 = y0 + extra if difficulty == "Hard" else rng.randint(2, 12)
        c = a * x0 + b * y0

        equation = tex(f"{sum_terms(term(a), term(b, 'y'))} = {number(c)}")
        setup = (
            f"{intro.format(a=a, b=b)} The equation {equation} relates the number of "
            f"{x_item}, {tex('x')}, and the number of {y_item}, {tex('y')}, in an order that "
            f"{outcome.format(c=c)}."
        )
        answer = number(y0)

        if difficulty == "Hard":
            text = (
                f"{setup} The order included {number(extra)} more {x_item} than {y_item}. "
                f"How many {y_item} did it include?"
            )
            rationale = (
                f"Since {tex(f'x = y + {number(extra)}')}, substitute: "
                f"{tex(f'{number(a)}(y + {number(extra)}) + {term(b, 'y')} = {number(c)}')}, so "
                f"{tex(f'{term(a + b, 'y')} = {number(c - a * extra)}')} and {tex(f'y = {answer}')}."
            )
            near_misses = [number(x0), number(y0 - extra), number(c // (a + b)), number(x0 + y0)]
        else:
            text = f"{setup} If the order included {number(x0)} {x_item}, how many {y_item} did it include?"
            rationale = (
                f"Substitute {tex(f'x = {number(x0)}')}: {tex(f'{number(a * x0)} + {term(b, 'y')} = {number(c)}')}, "
                f"so {tex(f'{term(b, 'y')} = {number(c - a * x0)}')} and {tex(f'y = {answer}')}."
            )
            near_misses = [number(x0), number(c - a * x0), number(c // b), number(y0 + 1)]

        if qtype == "SPR":
            return self.spr(text=text, answer=answer, rationale=rationale, difficulty=difficulty)

        return self.mcq(
            text=text,
            correct=answer,
            distractors=pick_distractors(answer, near_misses, pad=numeric_variants(y0)),
            rationale=rationale,
            difficulty=difficulty,
            rng=rng,
        )


TEMPLATES = [
    LinearEquationTemplate(),
    LinearSystemTemplate(),
    SlopeTemplate(),
    LineGraphTemplate(),
    TwoVariableModelTemplate(),
]


class LinearInequalityTemplate(Template):
    """Identify a value that satisfies a linear inequality."""

    key = "linear_inequality"
    domain = DOMAIN
    skill = "Linear inequalities in one or two variables"
    types = ("MCQ",)

    def build(self, rng: random.Random, qtype: str, difficulty: str) -> Question:
        a = nonzero(rng, 2, 9)
        b = rng.randint(-12, 12)
        boundary = nonzero(rng, -6, 9)
        c = a * boundary + b

        # "<" and ">" keep the boundary itself out of the solution set, so a
        # distractor sitting exactly on it is wrong for a clear reason.
        strict = rng.choice([True, False])
        greater = rng.choice([True, False])
        symbol = (">" if strict else "\\geq") if greater else ("<" if strict else "\\leq")

        def satisfies(value: int) -> bool:
            left = a * value + b
            if greater:
                return left > c if strict else left >= c
            return left < c if strict else left <= c

        step = 1 if greater else -1
        correct = next(
            boundary + step * offset
            for offset in range(0 if not strict else 1, 12)
            if satisfies(boundary + step * offset)
        )
        wrong = [boundary - step * offset for offset in range(1, 12) if not satisfies(boundary - step * offset)]
        if not strict:
            wrong.insert(0, boundary - step)

        inequality = tex(f"{linear(a, b)} {symbol} {number(c)}")
        answer = number(correct)
        rationale = (
            f"Solving gives {tex(f'x {symbol} {number(boundary)}')}. "
            f"Of the choices, only {tex(answer)} satisfies it."
        )

        return self.mcq(
            text=f"Which value of {tex('x')} is a solution to the inequality {inequality}?",
            correct=answer,
            distractors=pick_distractors(answer, (number(value) for value in wrong)),
            rationale=rationale,
            difficulty=difficulty,
            rng=rng,
        )


TEMPLATES.append(LinearInequalityTemplate())
TEMPLATES.append(SlopeFromGraphTemplate())
