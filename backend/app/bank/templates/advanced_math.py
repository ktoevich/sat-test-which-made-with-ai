"""Advanced Math templates: quadratics, exponentials, function notation."""

from __future__ import annotations

import random

from ..latex import linear, number, sum_terms, term, tex
from .base import Question, Template, nonzero, numeric_variants, pick_distractors

DOMAIN = "Advanced Math"


class QuadraticRootsTemplate(Template):
    """Solve a factorable quadratic equation."""

    key = "quadratic_roots"
    domain = DOMAIN
    skill = "Nonlinear equations in one variable and systems of equations in two variables"
    types = ("MCQ", "SPR")

    def build(self, rng: random.Random, qtype: str, difficulty: str) -> Question:
        bound = {"Easy": 6, "Medium": 9, "Hard": 12}[difficulty]
        r1, r2 = nonzero(rng, -bound, bound), nonzero(rng, -bound, bound)
        while r1 == r2:
            r2 = nonzero(rng, -bound, bound)

        b, c = -(r1 + r2), r1 * r2
        equation = tex(f"{sum_terms('x^2', term(b), number(c))} = 0")

        asks_sum = difficulty == "Hard"
        target = r1 + r2 if asks_sum else max(r1, r2)
        answer = number(target)
        label = "the sum of the solutions" if asks_sum else "the greater solution"
        factors = "".join(f"(x {'-' if root >= 0 else '+'} {number(abs(root))})" for root in (r1, r2))
        rationale = (
            f"The equation factors as {tex(f'{factors} = 0')}, "
            f"so the solutions are {tex(number(r1))} and {tex(number(r2))}."
        )
        text = f"What is {label} of the equation {equation}?"

        if qtype == "SPR":
            return self.spr(text=text, answer=answer, rationale=rationale, difficulty=difficulty)

        distractors = pick_distractors(
            answer,
            [number(min(r1, r2)), number(-target), number(r1 * r2), number(target + 1)],
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


class ExponentialTemplate(Template):
    """Evaluate or identify an exponential model."""

    key = "exponential_growth"
    domain = DOMAIN
    skill = "Nonlinear functions"
    types = ("MCQ",)

    def build(self, rng: random.Random, qtype: str, difficulty: str) -> Question:
        initial = rng.choice([20, 25, 40, 50, 80, 120, 200])
        rate = rng.choice([5, 10, 20, 25, 50])
        years = {"Easy": 1, "Medium": 2, "Hard": 3}[difficulty]
        growing = rng.choice([True, False])

        factor = 1 + rate / 100 if growing else 1 - rate / 100
        value = initial * factor**years
        answer = number(round(value, 2))
        direction = "increases" if growing else "decreases"

        rationale = (
            f"Each year the amount is multiplied by {tex(number(round(factor, 2)))}, so after "
            f"{years} year(s) it is {tex(f'{number(initial)} \\cdot {number(round(factor, 2))}^{{{years}}}')} "
            f"= {tex(answer)}."
        )

        distractors = pick_distractors(
            answer,
            [
                number(round(initial * (1 + (rate / 100 if not growing else -rate / 100)) ** years, 2)),
                number(round(initial * factor * years, 2)),
                number(round(initial + initial * rate / 100 * years, 2)),
                number(round(value * 2, 2)),
            ],
            pad=numeric_variants(value, digits=2),
        )
        return self.mcq(
            text=(
                f"A quantity starts at {number(initial)} and {direction} by {number(rate)}% each year. "
                f"What is the quantity after {years} year(s)?"
            ),
            correct=answer,
            distractors=distractors,
            rationale=rationale,
            difficulty=difficulty,
            rng=rng,
        )


class FunctionValueTemplate(Template):
    """Evaluate a function at a given input."""

    key = "function_value"
    domain = DOMAIN
    skill = "Nonlinear functions"
    types = ("MCQ", "SPR")
    difficulties = ("Easy", "Medium")

    def build(self, rng: random.Random, qtype: str, difficulty: str) -> Question:
        a, b = nonzero(rng, 2, 8), rng.randint(-10, 10)
        point = nonzero(rng, -6, 6)

        if difficulty == "Easy":
            definition = f"f(x) = {linear(a, b)}"
            value = a * point + b
        else:
            c = nonzero(rng, 1, 4)
            definition = f"f(x) = {sum_terms(term(c, 'x^2'), term(a), number(b))}"
            value = c * point**2 + a * point + b

        answer = number(value)
        rationale = f"Substitute {tex(f'x = {number(point)}')} into {tex(definition)} to get {tex(answer)}."
        text = f"The function {tex(definition)} is defined for all real numbers. What is the value of {tex(f'f({number(point)})')}?"

        if qtype == "SPR":
            return self.spr(text=text, answer=answer, rationale=rationale, difficulty=difficulty)

        distractors = pick_distractors(
            answer,
            [number(-value), number(value + a), number(value - b), number(a * point)],
            pad=numeric_variants(value),
        )
        return self.mcq(
            text=text,
            correct=answer,
            distractors=distractors,
            rationale=rationale,
            difficulty=difficulty,
            rng=rng,
        )


TEMPLATES = [QuadraticRootsTemplate(), ExponentialTemplate(), FunctionValueTemplate()]


class EquivalentExpressionsTemplate(Template):
    """Recognise the expanded or factored form of an expression."""

    key = "equivalent_expressions"
    domain = DOMAIN
    skill = "Equivalent expressions"
    types = ("MCQ",)

    def build(self, rng: random.Random, qtype: str, difficulty: str) -> Question:
        p, q = nonzero(rng, -9, 9), nonzero(rng, -9, 9)
        lead = 1 if difficulty == "Easy" else nonzero(rng, 2, 4)

        factored = f"({term(lead, 'x')} {'+' if p >= 0 else '-'} {number(abs(p))})(x {'+' if q >= 0 else '-'} {number(abs(q))})"
        middle, constant = lead * q + p, p * q
        expanded = sum_terms(term(lead, "x^2"), term(middle), number(constant))

        expand = difficulty != "Hard"
        if expand:
            text = f"Which expression is equivalent to {tex(factored)}?"
            answer = tex(expanded)
            wrong = [
                tex(sum_terms(term(lead, "x^2"), term(middle), number(-constant))),
                tex(sum_terms(term(lead, "x^2"), term(-middle), number(constant))),
                tex(sum_terms(term(lead, "x^2"), term(p + q), number(constant))),
                tex(sum_terms(term(lead, "x^2"), term(middle + 2), number(constant))),
            ]
        else:
            text = f"Which expression is equivalent to {tex(expanded)}?"
            answer = tex(factored)
            wrong = [
                tex(f"({term(lead, 'x')} {'-' if p >= 0 else '+'} {number(abs(p))})(x {'+' if q >= 0 else '-'} {number(abs(q))})"),
                tex(f"({term(lead, 'x')} {'+' if p >= 0 else '-'} {number(abs(p))})(x {'-' if q >= 0 else '+'} {number(abs(q))})"),
                tex(f"({term(lead, 'x')} {'+' if q >= 0 else '-'} {number(abs(q))})(x {'+' if p >= 0 else '-'} {number(abs(p))})"),
                tex(f"({term(lead, 'x')} {'+' if p >= 0 else '-'} {number(abs(p) + 1)})(x {'+' if q >= 0 else '-'} {number(abs(q))})"),
            ]

        # With lead == 1 several of the "plausible" wrong forms collapse onto the
        # answer, so keep a supply of shifted variants behind them.
        if expand:
            pad = (
                tex(sum_terms(term(lead, "x^2"), term(middle + delta), number(constant)))
                for delta in (1, -1, 3, -3, 4, -4, 5, -5, 6, -6)
            )
        else:
            pad = (
                tex(
                    f"({term(lead, 'x')} {'+' if p >= 0 else '-'} {number(abs(p))})"
                    f"(x {'+' if q >= 0 else '-'} {number(abs(q) + delta)})"
                )
                for delta in (1, -1, 2, -2, 3, -3, 4, -4)
            )

        rationale = (
            f"Multiplying out, {tex(factored)} = {tex(expanded)}, so the two forms are equivalent."
        )
        return self.mcq(
            text=text,
            correct=answer,
            distractors=pick_distractors(answer, wrong, pad=pad),
            rationale=rationale,
            difficulty=difficulty,
            rng=rng,
        )


TEMPLATES.append(EquivalentExpressionsTemplate())


class ParabolaGraphTemplate(Template):
    """Read a parabola off a grid: its vertex, its extreme value, or a shift.

    The harder route's Nonlinear functions row asks for "harder parabolas,
    graph shifts", and this is the skill that most often carries a graph on the
    real test, so the curve is drawn rather than described.
    """

    key = "parabola_graph"
    domain = DOMAIN
    skill = "Nonlinear functions"
    types = ("MCQ", "SPR")

    GRID_END = 10

    def build(self, rng: random.Random, qtype: str, difficulty: str) -> Question:
        lead = rng.choice([1, -1, 1, -1, 2, -2])
        h = rng.randint(-4, 4)
        k = rng.randint(-6, 6)
        image = self._plot(lead, h, k)
        opens = "upward" if lead > 0 else "downward"
        extreme = "minimum" if lead > 0 else "maximum"

        if difficulty == "Hard":
            shift = nonzero(rng, -4, 4)
            moved = h + shift
            answer = tex(f"({number(moved)}, {number(k)})")
            inner = f"x {'-' if shift >= 0 else '+'} {number(abs(shift))}"
            text = (
                f"The graph of {tex('y = f(x)')} is shown in the {tex('xy')}-plane above. If "
                f"{tex(f'g(x) = f({inner})')}, what are the coordinates of the vertex of the graph "
                f"of {tex('y = g(x)')}?"
            )
            rationale = (
                f"The vertex of {tex('f')} is at {tex(f'({number(h)}, {number(k)})')}. Replacing "
                f"{tex('x')} with {tex(inner)} shifts the graph {number(abs(shift))} "
                f"{'right' if shift > 0 else 'left'}, so the vertex moves to {answer}."
            )
            distractors = pick_distractors(
                answer,
                [
                    tex(f"({number(h - shift)}, {number(k)})"),
                    tex(f"({number(h)}, {number(k + shift)})"),
                    tex(f"({number(h)}, {number(k - shift)})"),
                    tex(f"({number(moved)}, {number(-k)})"),
                ],
                pad=(tex(f"({number(moved + dx)}, {number(k + dy)})") for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1))),
            )
        elif difficulty == "Medium":
            answer = tex(f"({number(h)}, {number(k)})")
            text = (
                f"The graph of a parabola is shown in the {tex('xy')}-plane above. What are the "
                "coordinates of its vertex?"
            )
            rationale = (
                f"The parabola opens {opens} and turns at {answer}, which is its vertex."
            )
            distractors = pick_distractors(
                answer,
                [
                    tex(f"({number(k)}, {number(h)})"),
                    tex(f"({number(-h)}, {number(k)})"),
                    tex(f"({number(h)}, {number(-k)})"),
                    tex(f"({number(-h)}, {number(-k)})"),
                ],
                pad=(tex(f"({number(h + dx)}, {number(k + dy)})") for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1))),
            )
        else:
            answer = number(k)
            text = (
                f"The graph of {tex('y = f(x)')} is shown in the {tex('xy')}-plane above. What is "
                f"the {extreme} value of {tex('f')}?"
            )
            rationale = (
                f"The parabola opens {opens}, so its {extreme} is the {tex('y')}-coordinate of the "
                f"vertex {tex(f'({number(h)}, {number(k)})')}, which is {tex(answer)}."
            )
            distractors = pick_distractors(
                answer,
                [number(h), number(-k), number(k + 1), number(k - 2)],
                pad=numeric_variants(k),
            )

        # A grid-in takes a plain number, so the coordinate-pair variants are
        # answered as multiple choice only.
        if qtype == "SPR":
            if difficulty != "Easy":
                answer = number(k)
                text = (
                    f"The graph of {tex('y = f(x)')} is shown in the {tex('xy')}-plane above. What "
                    f"is the {extreme} value of {tex('f')}?"
                )
                rationale = (
                    f"The parabola opens {opens}, so its {extreme} is the {tex('y')}-coordinate of "
                    f"the vertex {tex(f'({number(h)}, {number(k)})')}, which is {tex(answer)}."
                )
            return self.spr(
                text=text, answer=answer, rationale=rationale, difficulty=difficulty, image=image
            )

        return self.mcq(
            text=text,
            correct=answer,
            distractors=distractors,
            rationale=rationale,
            difficulty=difficulty,
            rng=rng,
            image=image,
        )

    def _plot(self, lead: int, h: int, k: int) -> dict:
        """The parabola as a polyline, clipped to the visible grid."""
        end = self.GRID_END
        points = []
        steps = int(end * 2 / 0.25) + 1
        for index in range(steps + 1):
            x = -end + index * 0.25
            y = lead * (x - h) ** 2 + k
            if abs(y) > end:
                # Break the polyline where the curve leaves the grid.
                if points and points[-1] != "":
                    points.append("")
                continue
            points.append(f"{round(x, 2)},{round(y, 2)}")

        runs = [run for run in " ".join(points).split("  ") if run.strip()]
        draw = "".join(
            f'<polyline points="{run.strip()}" fill="none" stroke="#2563eb" stroke-width="2"/>'
            for run in runs
        )
        draw += f'<circle cx="{h}" cy="{k}" r="0.18" fill="#2563eb"/>'
        alt = (
            f"Coordinate-plane graph. A parabola opening "
            f"{'upward' if lead > 0 else 'downward'} is graphed in the xy-plane, with its vertex "
            f"marked at ({number(h)}, {number(k)})."
        )
        return {"xEnd": end, "yEnd": end, "step": 2, "alt": alt, "draw": draw}


TEMPLATES.append(ParabolaGraphTemplate())
