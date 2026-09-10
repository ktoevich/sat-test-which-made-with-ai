"""Geometry and Trigonometry templates: right triangles, circles, angles."""

from __future__ import annotations

import math
import random

from .. import figures
from ..latex import number, signed, tex
from .base import Question, Template, nonzero, numeric_variants, pick_distractors

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
                f"The right triangle shown has legs of length {number(leg_a)} and {number(leg_b)}. "
                f"What is the value of {tex('x')}, the length of its hypotenuse?"
            )
            rationale = (
                f"By the Pythagorean theorem, "
                f"{tex(f'{number(leg_a)}^2 + {number(leg_b)}^2 = {number(hypotenuse ** 2)}')}, "
                f"so the hypotenuse is {tex(answer)}."
            )
        else:
            answer = number(leg_b)
            text = (
                f"In the right triangle shown, the hypotenuse has length {number(hypotenuse)} and one "
                f"leg has length {number(leg_a)}. What is the value of {tex('x')}, the length of the "
                "other leg?"
            )
            rationale = (
                f"{tex(f'{number(hypotenuse)}^2 - {number(leg_a)}^2 = {number(leg_b ** 2)}')}, "
                f"so the other leg is {tex(answer)}."
            )

        image = figures.right_triangle(
            base=leg_a,
            height=leg_b,
            base_label=number(leg_a),
            height_label=number(leg_b) if find_hypotenuse else "x",
            hypotenuse_label="x" if find_hypotenuse else number(hypotenuse),
            unknown="hypotenuse" if find_hypotenuse else "height",
        )

        if qtype == "SPR":
            return self.spr(
                text=text, answer=answer, rationale=rationale, difficulty=difficulty, image=image
            )

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
            image=image,
        )


class CircleTemplate(Template):
    """Area of a circle from its radius or diameter; at Hard, read the center or
    radius off an expanded equation ``x^2 + y^2 + Dx + Ey + F = 0``."""

    key = "circle_measures"
    domain = DOMAIN
    skill = "Circles"
    types = ("MCQ",)

    def build(self, rng: random.Random, qtype: str, difficulty: str) -> Question:
        if difficulty == "Hard":
            return self._from_equation(rng, difficulty)

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

    def _from_equation(self, rng: random.Random, difficulty: str) -> Question:
        h, k = nonzero(rng, -6, 6), nonzero(rng, -6, 6)
        radius = rng.randint(2, 9)
        constant = h * h + k * k - radius * radius
        while constant == 0:
            radius = rng.randint(2, 9)
            constant = h * h + k * k - radius * radius

        equation = tex(f"x^2 + y^2 {signed(-2 * h)}x {signed(-2 * k)}y {signed(constant)} = 0")
        completed = tex(f"(x {signed(-h)})^2 + (y {signed(-k)})^2 = {number(radius ** 2)}")
        center = tex(f"({number(h)}, {number(k)})")
        rationale = (
            f"Complete the square in {tex('x')} and in {tex('y')}: {completed}. "
            f"This is a circle with center {center} and radius {tex(number(radius))}."
        )
        lead = f"In the {tex('xy')}-plane, the graph of {equation} is a circle."

        if rng.choice([True, False]):
            answer = number(radius)
            distractors = pick_distractors(
                answer,
                [
                    number(radius ** 2),
                    number(abs(constant)),
                    number(h * h + k * k),
                    number(2 * radius),
                ],
                pad=numeric_variants(radius),
            )
            text = f"{lead} What is the radius of the circle?"
        else:
            answer = center
            distractors = pick_distractors(
                answer,
                [
                    tex(f"({number(-h)}, {number(-k)})"),
                    tex(f"({number(h)}, {number(-k)})"),
                    tex(f"({number(-h)}, {number(k)})"),
                    tex(f"({number(2 * h)}, {number(2 * k)})"),
                ],
                pad=(tex(f"({number(h + dx)}, {number(k + dy)})") for dx, dy in ((1, 0), (0, 1), (-1, 0))),
            )
            text = f"{lead} What are the coordinates of the center of the circle?"

        return self.mcq(
            text=text,
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

        image = figures.labelled_triangle(
            angles=(first, second, third),
            labels=(f"{number(first)}°", f"{number(second)}°", "x°"),
        )
        text = (
            f"In the triangle shown, two angles measure {number(first)}° and {number(second)}°. "
            f"What is the value of {tex('x')}, the measure in degrees of the third angle?"
        )
        rationale = (
            f"The angles of a triangle sum to 180°, so the third angle is "
            f"{tex(f'180 - {number(first)} - {number(second)} = {answer}')}."
        )

        if qtype == "SPR":
            return self.spr(
                text=text, answer=answer, rationale=rationale, difficulty=difficulty, image=image
            )

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
            image=image,
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
                f"The rectangle shown has a width of {number(width)} and a height of "
                f"{number(height)}. What is its area?"
            )
            image = figures.rectangle(
                width_value=width,
                height_value=height,
                width_label=number(width),
                height_label=number(height),
            )
            rationale = f"Area is {tex(f'{number(width)} \\cdot {number(height)} = {number(value)}')}."
            wrong = [number(2 * (width + height)), number(width + height), number(value * 2)]
        elif difficulty == "Medium":
            base, height = rng.choice([4, 6, 8, 10, 12, 14]), rng.randint(3, 15)
            value = base * height // 2
            text = (
                f"The triangle shown has a base of {number(base)} and a height of "
                f"{number(height)}. What is its area?"
            )
            image = figures.triangle(
                base_value=base,
                height_value=height,
                base_label=number(base),
                height_label=number(height),
            )
            rationale = (
                f"Area is {tex(f'\\frac{{1}}{{2}} \\cdot {number(base)} \\cdot {number(height)} = {number(value)}')}."
            )
            wrong = [number(base * height), number(base + height), number(value + base)]
        else:
            length, width, height = (rng.randint(2, 9) for _ in range(3))
            value = length * width * height
            text = (
                f"The rectangular prism shown has edge lengths {number(length)}, {number(width)} "
                f"and {number(height)}. What is its volume?"
            )
            image = figures.prism(
                length=length,
                width_value=width,
                height_value=height,
                labels=(number(length), number(width), number(height)),
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
            return self.spr(
                text=text, answer=answer, rationale=rationale, difficulty=difficulty, image=image
            )

        return self.mcq(
            text=text,
            correct=answer,
            distractors=pick_distractors(answer, wrong, pad=numeric_variants(value)),
            rationale=rationale,
            difficulty=difficulty,
            rng=rng,
            image=image,
        )


TEMPLATES.append(AreaVolumeTemplate())
class CrossingAnglesTemplate(Template):
    """Vertical and adjacent angles at the intersection of two straight lines.

    The blueprint's easier route asks for "adjacent and vertical angles", which
    only means anything next to a picture: the question is which of the four
    angles around the crossing point the label sits in.
    """

    key = "crossing_angles"
    domain = DOMAIN
    skill = "Lines, angles, and triangles"
    types = ("MCQ", "SPR")
    difficulties = ("Easy", "Medium")

    CORNERS = ("upper right", "upper left", "lower left", "lower right")

    def build(self, rng: random.Random, qtype: str, difficulty: str) -> Question:
        given = rng.randint(25, 155)
        while given == 90:
            given = rng.randint(25, 155)

        index = rng.randrange(4)
        given_position = self.CORNERS[index]
        # The angle straight across is equal; either neighbour is supplementary.
        vertical = difficulty == "Easy"
        offset = 2 if vertical else rng.choice([1, 3])
        unknown_position = self.CORNERS[(index + offset) % 4]

        answer = number(given if vertical else 180 - given)
        rationale = (
            (
                f"The {unknown_position} angle is vertical to the {given_position} angle, and "
                f"vertical angles are equal, so {tex(f'x = {answer}')}."
            )
            if vertical
            else (
                f"The {unknown_position} and {given_position} angles sit on a straight line, so they "
                f"add to 180°: {tex(f'x = 180 - {number(given)} = {answer}')}."
            )
        )

        image = figures.crossing_lines(
            given=given, given_position=given_position, unknown_position=unknown_position
        )
        text = (
            f"In the figure shown, two straight lines cross. What is the value of {tex('x')}?"
        )

        if qtype == "SPR":
            return self.spr(
                text=text, answer=answer, rationale=rationale, difficulty=difficulty, image=image
            )

        distractors = pick_distractors(
            answer,
            [
                number(180 - int(answer)),
                number(90 - given if given < 90 else given - 90),
                number(360 - 2 * given) if 0 < 360 - 2 * given < 180 else number(given // 2),
                number(int(answer) + 10),
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
            image=image,
        )


TEMPLATES.append(CrossingAnglesTemplate())

