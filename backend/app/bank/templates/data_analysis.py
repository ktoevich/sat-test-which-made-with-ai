"""Problem-Solving and Data Analysis templates: percentages, rates, statistics."""

from __future__ import annotations

import random

from ..latex import fraction, number, tex
from .base import Question, Template, nonzero, numeric_variants, pick_distractors

DOMAIN = "Problem-Solving and Data Analysis"


class PercentChangeTemplate(Template):
    """Apply a percent increase or decrease."""

    key = "percent_change"
    domain = DOMAIN
    skill = "Percentages"
    types = ("MCQ", "SPR")

    def build(self, rng: random.Random, qtype: str, difficulty: str) -> Question:
        base = rng.choice([40, 60, 80, 120, 150, 200, 250, 400])
        percent = rng.choice([5, 10, 15, 20, 25, 40, 60])
        increase = rng.choice([True, False])

        change = base * percent / 100
        value = base + change if increase else base - change
        answer = number(round(value, 2))
        word = "increased" if increase else "decreased"

        rationale = (
            f"{number(percent)}% of {number(base)} is {tex(number(round(change, 2)))}, so the result is "
            f"{tex(f'{number(base)} {"+" if increase else "-"} {number(round(change, 2))} = {answer}')}."
        )
        text = (
            f"A value of {number(base)} is {word} by {number(percent)}%. "
            "What is the resulting value?"
        )

        if qtype == "SPR":
            return self.spr(text=text, answer=answer, rationale=rationale, difficulty=difficulty)

        opposite = base - change if increase else base + change
        distractors = pick_distractors(
            answer,
            [
                number(round(opposite, 2)),
                number(round(change, 2)),
                number(round(base * percent / 100 + percent, 2)),
                number(round(value + 10, 2)),
            ],
            pad=numeric_variants(value, digits=2),
        )
        return self.mcq(
            text=text,
            correct=answer,
            distractors=distractors,
            rationale=rationale,
            difficulty=difficulty,
            rng=rng,
        )


class MeanTemplate(Template):
    """Find the mean, or the missing value that produces a given mean."""

    key = "data_mean"
    domain = DOMAIN
    skill = "One-variable data: distributions and measures of center and spread"
    types = ("SPR", "MCQ")

    def build(self, rng: random.Random, qtype: str, difficulty: str) -> Question:
        size = {"Easy": 4, "Medium": 5, "Hard": 6}[difficulty]
        mean = rng.randint(6, 30)
        values = [mean + nonzero(rng, -6, 6) for _ in range(size - 1)]
        last = mean * size - sum(values)

        if difficulty == "Hard":
            listed = ", ".join(number(value) for value in values)
            answer = number(last)
            text = (
                f"A data set contains {size} values. {size - 1} of them are {listed}. "
                f"If the mean of all {size} values is {number(mean)}, what is the remaining value?"
            )
            rationale = (
                f"The values must total {tex(f'{size} \\cdot {number(mean)} = {number(mean * size)}')}; "
                f"the listed values total {tex(number(sum(values)))}, so the missing value is {tex(answer)}."
            )
        else:
            data = [*values, last]
            rng.shuffle(data)
            listed = ", ".join(number(value) for value in data)
            answer = number(mean)
            text = f"What is the mean of the data set {listed}?"
            rationale = (
                f"The values total {tex(number(sum(data)))}; dividing by {size} gives {tex(answer)}."
            )

        if qtype == "SPR":
            return self.spr(text=text, answer=answer, rationale=rationale, difficulty=difficulty)

        distractors = pick_distractors(
            answer,
            [
                number(int(answer) + 1),
                number(int(answer) - 2),
                number(int(answer) * 2),
                number(int(answer) + 5),
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


class UnitRateTemplate(Template):
    """Scale a proportional relationship."""

    key = "unit_rate"
    domain = DOMAIN
    skill = "Ratios, rates, proportional relationships, and units"
    types = ("MCQ", "SPR")
    difficulties = ("Easy", "Medium")

    def build(self, rng: random.Random, qtype: str, difficulty: str) -> Question:
        rate = rng.randint(3, 25)
        first = rng.randint(2, 9)
        second = rng.randint(10, 40)
        produced = rate * first
        answer = number(rate * second)

        text = (
            f"A machine produces {number(produced)} parts in {number(first)} minutes at a constant rate. "
            f"At this rate, how many parts does it produce in {number(second)} minutes?"
        )
        rationale = (
            f"The rate is {tex(f'\\frac{{{number(produced)}}}{{{number(first)}}} = {number(rate)}')} parts per minute, "
            f"so in {number(second)} minutes it produces {tex(answer)} parts."
        )

        if qtype == "SPR":
            return self.spr(text=text, answer=answer, rationale=rationale, difficulty=difficulty)

        distractors = pick_distractors(
            answer,
            [
                number(rate * second + rate),
                number(produced * second),
                number(rate),
                number(rate * (second - first)),
            ],
            pad=numeric_variants(rate * second),
        )
        return self.mcq(
            text=text,
            correct=answer,
            distractors=distractors,
            rationale=rationale,
            difficulty=difficulty,
            rng=rng,
        )


TEMPLATES = [PercentChangeTemplate(), MeanTemplate(), UnitRateTemplate()]


class ScatterplotTemplate(Template):
    """Read a prediction off a line of best fit."""

    key = "scatterplot_model"
    domain = DOMAIN
    skill = "Two-variable data: models and scatterplots"
    types = ("MCQ",)
    difficulties = ("Easy", "Medium")

    GRID_END = 10
    JITTER = (0.6, -0.5, 0.4, -0.7, 0.3, -0.3, 0.5)

    def build(self, rng: random.Random, qtype: str, difficulty: str) -> Question:
        slope = rng.choice([1, 2, -1, -2])
        intercept = rng.randint(-3, 3)

        # Keep the drawn segment and every plotted point inside the grid.
        span = max(2, min(self.GRID_END, (self.GRID_END - abs(intercept) - 1) // abs(slope)))
        query = rng.randint(-span, span)
        value = slope * query + intercept

        points = []
        for index, offset in enumerate(range(-span, span + 1)):
            jitter = self.JITTER[index % len(self.JITTER)]
            points.append(
                f'<circle cx="{offset}" cy="{round(slope * offset + intercept + jitter, 2)}" '
                f'r="0.22" fill="#0f172a"/>'
            )

        image = {
            "xEnd": self.GRID_END,
            "yEnd": self.GRID_END,
            "step": 2,
            "draw": (
                f'<line x1="{-span}" y1="{slope * -span + intercept}" '
                f'x2="{span}" y2="{slope * span + intercept}" stroke="#2563eb" stroke-width="2"/>'
                + "".join(points)
            ),
        }

        answer = number(value)
        rationale = (
            f"The line of best fit is {tex(f'y = {slope}x {'+' if intercept >= 0 else '-'} {number(abs(intercept))}')}"
            if intercept
            else f"The line of best fit is {tex(f'y = {slope}x')}"
        )
        rationale += f". At {tex(f'x = {number(query)}')} it predicts {tex(answer)}."

        return self.mcq(
            text=(
                "The scatterplot above shows a data set together with its line of best fit. "
                f"Based on the line of best fit, what is the predicted value of {tex('y')} when "
                f"{tex(f'x = {number(query)}')}?"
            ),
            correct=answer,
            distractors=pick_distractors(
                answer,
                [number(-value), number(slope * query), number(query + intercept)],
                pad=numeric_variants(value),
            ),
            rationale=rationale,
            difficulty=difficulty,
            rng=rng,
            image=image,
        )


class ProbabilityTableTemplate(Template):
    """Read a probability off a two-way frequency table."""

    key = "probability_table"
    domain = DOMAIN
    skill = "Probability and conditional probability"
    types = ("MCQ",)

    #: Each row is (column heading, phrase that fits "one of the ...").
    GROUPS = (
        (("Freshmen", "freshmen"), ("Seniors", "seniors")),
        (("Group A", "people in Group A"), ("Group B", "people in Group B")),
        (
            ("Morning session", "people in the morning session"),
            ("Evening session", "people in the evening session"),
        ),
    )
    CHOICES = (("Yes", "No"), ("Passed", "Did not pass"), ("Attended", "Did not attend"))

    def build(self, rng: random.Random, qtype: str, difficulty: str) -> Question:
        rows = rng.choice(self.GROUPS)
        cols = rng.choice(self.CHOICES)
        cells = [[rng.randint(4, 30) for _ in range(2)] for _ in range(2)]

        row_totals = [sum(row) for row in cells]
        col_totals = [cells[0][index] + cells[1][index] for index in range(2)]
        grand = sum(row_totals)

        header = f"<tr><th></th><th>{cols[0]}</th><th>{cols[1]}</th><th>Total</th></tr>"
        body = "".join(
            f"<tr><td>{rows[index][0]}</td><td>{cells[index][0]}</td>"
            f"<td>{cells[index][1]}</td><td>{row_totals[index]}</td></tr>"
            for index in range(2)
        )
        footer = f"<tr><td>Total</td><td>{col_totals[0]}</td><td>{col_totals[1]}</td><td>{grand}</td></tr>"
        table = f'<table class="question-table">{header}{body}{footer}</table>'

        conditional = difficulty != "Easy"
        if conditional:
            question = (
                f"If one of the {rows[0][1]} is selected at random, what is the probability "
                f'that the selected person is in the "{cols[0]}" category?'
            )
            correct_pair = (cells[0][0], row_totals[0])
            rationale = (
                f"Restrict to the {row_totals[0]} {rows[0][1]}; {cells[0][0]} of them are "
                f'"{cols[0]}".'
            )
            wrong_pairs = [(cells[0][0], grand), (cells[0][0], col_totals[0]), (row_totals[0], grand)]
        else:
            question = (
                "If one person is selected at random from the whole group, what is the probability "
                f'that the selected person is in the "{cols[0]}" category?'
            )
            correct_pair = (col_totals[0], grand)
            rationale = f'{col_totals[0]} of the {grand} people are in the "{cols[0]}" category.'
            wrong_pairs = [(cells[0][0], grand), (col_totals[0], col_totals[1]), (cells[1][0], grand)]

        answer = tex(fraction(*correct_pair))
        return self.mcq(
            text=f"{table}\nThe table above summarises a group of {grand} people. {question}",
            correct=answer,
            distractors=pick_distractors(
                answer,
                (tex(fraction(*pair)) for pair in wrong_pairs),
                pad=(tex(fraction(correct_pair[0] + delta, grand)) for delta in (1, -1, 2, -2, 3)),
            ),
            rationale=rationale,
            difficulty=difficulty,
            rng=rng,
        )


class MarginOfErrorTemplate(Template):
    """Interpret a sample estimate and its margin of error."""

    key = "margin_of_error"
    domain = DOMAIN
    skill = "Inference from sample statistics and margin of error"
    types = ("MCQ",)

    SUBJECTS = (
        ("residents of a city", "hours of sleep per night"),
        ("students at a school", "hours spent on homework per week"),
        ("members of a club", "books read per year"),
    )

    def build(self, rng: random.Random, qtype: str, difficulty: str) -> Question:
        population, measure = rng.choice(self.SUBJECTS)
        sample = rng.choice([200, 250, 400, 500, 750])
        estimate = round(rng.uniform(4, 12), 1)
        margin = rng.choice([0.2, 0.3, 0.4, 0.5, 0.8])

        low, high = round(estimate - margin, 2), round(estimate + margin, 2)
        answer = f"Between {number(low)} and {number(high)}"
        rationale = (
            f"The plausible range is the estimate plus or minus the margin of error: "
            f"{tex(f'{number(estimate)} \\pm {number(margin)}')}, that is {number(low)} to {number(high)}."
        )

        wrong = [
            f"Between {number(round(estimate - 2 * margin, 2))} and {number(round(estimate + 2 * margin, 2))}",
            f"Between {number(round(estimate - margin / 2, 2))} and {number(round(estimate + margin / 2, 2))}",
            f"Between {number(low)} and {number(estimate)}",
            f"Between {number(estimate)} and {number(high)}",
        ]

        return self.mcq(
            text=(
                f"A random sample of {number(sample)} {population} was surveyed about the mean number "
                f"of {measure}. The sample mean was {number(estimate)} with a margin of error of "
                f"{number(margin)}. Which is the most plausible range for the mean of the whole population?"
            ),
            correct=answer,
            distractors=pick_distractors(answer, wrong),
            rationale=rationale,
            difficulty=difficulty,
            rng=rng,
        )


class StatisticalClaimTemplate(Template):
    """Decide what a study design does and does not support."""

    key = "statistical_claim"
    domain = DOMAIN
    skill = "Evaluating statistical claims: observational studies and experiments"
    types = ("MCQ",)
    difficulties = ("Medium", "Hard")

    STUDIES = (
        ("a new study method", "test scores", "students at a large university"),
        ("a daily walking routine", "resting heart rate", "adults in a city"),
        ("a revised training plan", "completion times", "members of a running club"),
    )

    def build(self, rng: random.Random, qtype: str, difficulty: str) -> Question:
        treatment, outcome, population = rng.choice(self.STUDIES)
        random_sample = rng.choice([True, False])
        random_assignment = rng.choice([True, False])

        selection = (
            f"were selected at random from all {population}"
            if random_sample
            else f"volunteered from among {population}"
        )
        assignment = (
            "randomly assigned to either use it or not"
            if random_assignment
            else "allowed to choose whether to use it"
        )

        causal = (
            f"There is a cause-and-effect relationship between {treatment} and {outcome}, "
            f"and the conclusion can be generalized to all {population}."
        )
        causal_only = (
            f"There is a cause-and-effect relationship between {treatment} and {outcome}, "
            "but the conclusion cannot be generalized beyond the participants."
        )
        association_general = (
            f"There is an association between {treatment} and {outcome} that can be generalized "
            f"to all {population}, but cause and effect cannot be concluded."
        )
        association_only = (
            f"There is an association between {treatment} and {outcome} among the participants, "
            "but neither cause and effect nor generalization can be concluded."
        )

        if random_sample and random_assignment:
            answer, reason = causal, "random selection allows generalization and random assignment allows a causal claim"
        elif random_assignment:
            answer, reason = causal_only, "random assignment allows a causal claim, but without random selection the result does not generalize"
        elif random_sample:
            answer, reason = association_general, "random selection allows generalization, but without random assignment only an association can be claimed"
        else:
            answer, reason = association_only, "without random selection or random assignment, only an association among the participants can be claimed"

        options = [causal, causal_only, association_general, association_only]
        return self.mcq(
            text=(
                f"A researcher studied whether {treatment} affects {outcome}. The participants "
                f"{selection}, and were {assignment}. The group that used it showed a significantly "
                "better result. Which conclusion is best supported by this study?"
            ),
            correct=answer,
            distractors=pick_distractors(answer, options),
            rationale=f"Here {reason}.",
            difficulty=difficulty,
            rng=rng,
        )


TEMPLATES.extend(
    [
        ScatterplotTemplate(),
        ProbabilityTableTemplate(),
        MarginOfErrorTemplate(),
        StatisticalClaimTemplate(),
    ]
)
