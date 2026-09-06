"""Algebra templates: linear equations, systems, linear functions."""

from __future__ import annotations

import random

from ..latex import fraction, linear, number, paren, sum_terms, tex, term
from .base import Question, Template, nonzero, numeric_variants, pick_distractors

DOMAIN = "Algebra"


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

        # Keep both endpoints of the drawn segment inside the grid.
        span = min(self.GRID_END, (self.GRID_END - abs(intercept)) // max(1, abs(slope)))
        span = max(2, span)
        x1, x2 = -span, span
        y1, y2 = slope * x1 + intercept, slope * x2 + intercept

        equation = f"y = {linear(slope, intercept)}"
        answer = tex(equation)
        rationale = (
            f"The line crosses the {tex('y')}-axis at {tex(f'(0, {number(intercept)})')} and rises "
            f"{number(slope)} unit(s) for every 1 unit to the right, so its equation is {answer}."
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
            "draw": (
                f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#2563eb" stroke-width="2"/>'
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


TEMPLATES = [
    LinearEquationTemplate(),
    LinearSystemTemplate(),
    SlopeTemplate(),
    LineGraphTemplate(),
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
