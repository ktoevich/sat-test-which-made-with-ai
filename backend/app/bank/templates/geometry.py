"""Geometry and Trigonometry templates: right triangles, circles, angles."""

from __future__ import annotations

import math
import random

from ..latex import number, tex
from .base import Question, Template, numeric_variants, pick_distractors

DOMAIN = "Geometry and Trigonometry"

#: Primitive Pythagorean triples, scaled up to vary the numbers.
TRIPLES = ((3, 4, 5), (5, 12, 13), (8, 15, 17), (7, 24, 25), (20, 21, 29))


class RightTriangleTemplate(Template):
    """Find a missing side of a right triangle."""

    key = "right_triangle"
    domain = DOMAIN
    skill = "Right triangles and trigonometry"
    types = ("SPR", "MCQ")

    def build(self, rng: random.Random, qtype: str, difficulty: str) -> Question:
        leg_a, leg_b, hypotenuse = rng.choice(TRIPLES)
        scale = {"Easy": 1, "Medium": rng.randint(2, 3), "Hard": rng.randint(3, 5)}[difficulty]
        leg_a, leg_b, hypotenuse = leg_a * scale, leg_b * scale, hypotenuse * scale

        find_hypotenuse = difficulty != "Hard"
        if find_hypotenuse:
            answer = number(hypotenuse)
            text = (
                f"In a right triangle, the legs have lengths {number(leg_a)} and {number(leg_b)}. "
                "What is the length of the hypotenuse?"
            )
            rationale = (
                f"By the Pythagorean theorem, "
                f"{tex(f'{number(leg_a)}^2 + {number(leg_b)}^2 = {number(hypotenuse ** 2)}')}, "
                f"so the hypotenuse is {tex(answer)}."
            )
        else:
            answer = number(leg_b)
            text = (
                f"In a right triangle, the hypotenuse has length {number(hypotenuse)} and one leg has "
                f"length {number(leg_a)}. What is the length of the other leg?"
            )
            rationale = (
                f"{tex(f'{number(hypotenuse)}^2 - {number(leg_a)}^2 = {number(leg_b ** 2)}')}, "
                f"so the other leg is {tex(answer)}."
            )

        if qtype == "SPR":
            return self.spr(text=text, answer=answer, rationale=rationale, difficulty=difficulty)

        distractors = pick_distractors(
            answer,
            [
                number(leg_a + leg_b),
                number(abs(leg_b - leg_a)),
                number(round(math.sqrt(leg_a**2 + leg_b**2) + 1, 2)),
                number(leg_a),
            ],
            pad=numeric_variants(int(answer)),
        )
        return self.mcq(
            text=text,
            correct=answer,
            distractors=distractors,
            rationale=rationale,
            difficulty=difficulty,
            rng=rng,
        )


class CircleTemplate(Template):
    """Area or circumference of a circle, in terms of pi."""

    key = "circle_measures"
    domain = DOMAIN
    skill = "Circles"
    types = ("MCQ",)
    difficulties = ("Easy", "Medium")

    def build(self, rng: random.Random, qtype: str, difficulty: str) -> Question:
        radius = rng.randint(2, 14)
        from_diameter = difficulty == "Medium"
        given = radius * 2 if from_diameter else radius
        label = "diameter" if from_diameter else "radius"

        answer = tex(f"{number(radius ** 2)}\\pi")
        rationale = (
            (f"The radius is half the diameter, {tex(number(radius))}. " if from_diameter else "")
            + f"Area is {tex('\\pi r^2')} = {answer}."
        )

        distractors = pick_distractors(
            answer,
            [
                tex(f"{number(2 * radius)}\\pi"),
                tex(f"{number(radius)}\\pi"),
                tex(f"{number(4 * radius ** 2)}\\pi"),
                tex(f"{number(radius ** 2)}"),
            ],
            pad=(tex(f"{number(radius ** 2 + delta)}\\pi") for delta in (1, -1, 2, -2, 4, -4)),
        )
        return self.mcq(
            text=f"A circle has a {label} of {number(given)}. What is the area of the circle?",
            correct=answer,
            distractors=distractors,
            rationale=rationale,
            difficulty=difficulty,
            rng=rng,
        )


class TriangleAngleTemplate(Template):
    """Find a missing angle."""

    key = "triangle_angles"
    domain = DOMAIN
    skill = "Lines, angles, and triangles"
    types = ("SPR", "MCQ")
    difficulties = ("Easy", "Medium")

    def build(self, rng: random.Random, qtype: str, difficulty: str) -> Question:
        first = rng.randint(25, 80)
        second = rng.randint(25, 170 - first)
        third = 180 - first - second
        answer = number(third)

        text = (
            f"Two angles of a triangle measure {number(first)}° and {number(second)}°. "
            "What is the measure, in degrees, of the third angle?"
        )
        rationale = (
            f"The angles of a triangle sum to 180°, so the third angle is "
            f"{tex(f'180 - {number(first)} - {number(second)} = {answer}')}."
        )

        if qtype == "SPR":
            return self.spr(text=text, answer=answer, rationale=rationale, difficulty=difficulty)

        distractors = pick_distractors(
            answer,
            [
                number(180 - first),
                number(first + second),
                number(90 - third if third < 90 else third + 15),
                number(third + 10),
            ],
            pad=numeric_variants(third),
        )
        return self.mcq(
            text=text,
            correct=answer,
            distractors=distractors,
            rationale=rationale,
            difficulty=difficulty,
            rng=rng,
        )


TEMPLATES = [RightTriangleTemplate(), CircleTemplate(), TriangleAngleTemplate()]


class AreaVolumeTemplate(Template):
    """Area of a rectangle or triangle, or the volume of a solid."""

    key = "area_volume"
    domain = DOMAIN
    skill = "Area and volume"
    types = ("MCQ", "SPR")

    def build(self, rng: random.Random, qtype: str, difficulty: str) -> Question:
        if difficulty == "Easy":
            width, height = rng.randint(3, 15), rng.randint(3, 15)
            value = width * height
            text = (
                f"A rectangle has a width of {number(width)} and a height of {number(height)}. "
                "What is its area?"
            )
            rationale = f"Area is {tex(f'{number(width)} \\cdot {number(height)} = {number(value)}')}."
            wrong = [number(2 * (width + height)), number(width + height), number(value * 2)]
        elif difficulty == "Medium":
            base, height = rng.choice([4, 6, 8, 10, 12, 14]), rng.randint(3, 15)
            value = base * height // 2
            text = (
                f"A triangle has a base of {number(base)} and a height of {number(height)}. "
                "What is its area?"
            )
            rationale = (
                f"Area is {tex(f'\\frac{{1}}{{2}} \\cdot {number(base)} \\cdot {number(height)} = {number(value)}')}."
            )
            wrong = [number(base * height), number(base + height), number(value + base)]
        else:
            length, width, height = (rng.randint(2, 9) for _ in range(3))
            value = length * width * height
            text = (
                f"A rectangular prism has edge lengths {number(length)}, {number(width)} and "
                f"{number(height)}. What is its volume?"
            )
            rationale = (
                f"Volume is {tex(f'{number(length)} \\cdot {number(width)} \\cdot {number(height)} = {number(value)}')}."
            )
            wrong = [
                number(length + width + height),
                number(2 * (length * width + length * height + width * height)),
                number(length * width),
            ]

        answer = number(value)
        if qtype == "SPR":
            return self.spr(text=text, answer=answer, rationale=rationale, difficulty=difficulty)

        return self.mcq(
            text=text,
            correct=answer,
            distractors=pick_distractors(answer, wrong, pad=numeric_variants(value)),
            rationale=rationale,
            difficulty=difficulty,
            rng=rng,
        )


TEMPLATES.append(AreaVolumeTemplate())
