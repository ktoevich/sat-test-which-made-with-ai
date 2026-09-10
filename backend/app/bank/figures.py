"""Finished SVG diagrams for questions that are not drawn on a coordinate plane.

Two kinds of figure reach the browser. A question set on the ``xy``-plane ships
the descriptor ``{xEnd, yEnd, step, draw}`` and the frontend draws the axes
around it; anything else — a triangle, a bar chart, two crossing lines — ships
finished SVG as a string. This module builds the second kind.

Every figure carries an ``aria-label`` describing it in prose, the way the
College Board's own bank labels its art. Screen readers read it out, and the
Markdown export prints it as the figure's caption, so a question stays
answerable wherever the picture itself cannot follow.
"""

from __future__ import annotations

import html
import math
from typing import Sequence

#: Outlines and any text that is part of the figure.
INK = "#0f172a"
#: The part of the figure the question is actually about.
ACCENT = "#2563eb"
#: Axis numbers, tick marks, category names.
MUTED = "#64748b"
#: Light wash inside a closed shape.
WASH = "#dbeafe"
#: Grid lines behind a chart.
GRID = "#e2e8f0"

_FONT = 'font-family="system-ui, -apple-system, sans-serif"'


def _n(value: float) -> str:
    """A coordinate trimmed to two decimals, without a trailing ``.0``."""
    return f"{value:.2f}".rstrip("0").rstrip(".") or "0"


def svg(body: str, *, width: float, height: float, label: str) -> str:
    """Wrap figure markup in a labelled ``<svg>`` root."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_n(width)} {_n(height)}" '
        f'class="question-diagram no-copy" role="img" aria-label="{html.escape(label)}">'
        f"{body}</svg>"
    )


def label_of(markup: str) -> str | None:
    """The ``aria-label`` of a figure built here, for captions and exports."""
    start = markup.find('aria-label="')
    if start < 0:
        return None
    start += len('aria-label="')
    end = markup.find('"', start)
    return html.unescape(markup[start:end]) if end > start else None


# -- primitives ------------------------------------------------------------


def text(
    x: float,
    y: float,
    body: str,
    *,
    size: float = 14,
    anchor: str = "middle",
    fill: str = INK,
    weight: str = "400",
    italic: bool = False,
) -> str:
    style = ' font-style="italic"' if italic else ""
    return (
        f'<text x="{_n(x)}" y="{_n(y)}" {_FONT} font-size="{_n(size)}" '
        f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{style}>'
        f"{html.escape(body)}</text>"
    )


def line(x1: float, y1: float, x2: float, y2: float, *, color: str = INK, width: float = 2, dash: str = "") -> str:
    stroke = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<line x1="{_n(x1)}" y1="{_n(y1)}" x2="{_n(x2)}" y2="{_n(y2)}" '
        f'stroke="{color}" stroke-width="{_n(width)}" stroke-linecap="round"{stroke}/>'
    )


def polygon(points: Sequence[tuple[float, float]], *, fill: str = WASH, color: str = INK, width: float = 2) -> str:
    body = " ".join(f"{_n(x)},{_n(y)}" for x, y in points)
    return (
        f'<polygon points="{body}" fill="{fill}" stroke="{color}" '
        f'stroke-width="{_n(width)}" stroke-linejoin="round"/>'
    )


def right_angle_mark(corner: tuple[float, float], along: tuple[float, float], up: tuple[float, float], size: float = 13) -> str:
    """The little square that marks a 90° corner, drawn inside the angle."""
    cx, cy = corner
    ax, ay = _unit(along, corner)
    ux, uy = _unit(up, corner)
    points = [
        (cx + ax * size, cy + ay * size),
        (cx + (ax + ux) * size, cy + (ay + uy) * size),
        (cx + ux * size, cy + uy * size),
    ]
    body = " ".join(f"{_n(x)},{_n(y)}" for x, y in points)
    return f'<polyline points="{body}" fill="none" stroke="{INK}" stroke-width="1.5"/>'


def _unit(point: tuple[float, float], origin: tuple[float, float]) -> tuple[float, float]:
    dx, dy = point[0] - origin[0], point[1] - origin[1]
    length = math.hypot(dx, dy) or 1
    return dx / length, dy / length


def angle_arc(
    center: tuple[float, float],
    start_deg: float,
    end_deg: float,
    radius: float,
    *,
    color: str = ACCENT,
) -> str:
    """An arc sweeping counter-clockwise from ``start_deg`` to ``end_deg``.

    Angles are the ordinary mathematical ones, measured from the positive
    ``x``-axis; the screen's ``y`` runs the other way, which is why the sines
    are negated and the sweep flag is 0.
    """
    cx, cy = center
    x1, y1 = cx + radius * math.cos(math.radians(start_deg)), cy - radius * math.sin(math.radians(start_deg))
    x2, y2 = cx + radius * math.cos(math.radians(end_deg)), cy - radius * math.sin(math.radians(end_deg))
    large = 1 if abs(end_deg - start_deg) > 180 else 0
    return (
        f'<path d="M {_n(x1)} {_n(y1)} A {_n(radius)} {_n(radius)} 0 {large} 0 {_n(x2)} {_n(y2)}" '
        f'fill="none" stroke="{color}" stroke-width="2"/>'
    )


def clip_line(slope, intercept, edge: int) -> tuple[tuple[float, float], tuple[float, float]]:
    """Where ``y = slope·x + intercept`` enters and leaves the square grid.

    Clipping the two ends independently is what makes a drawn line reach both
    edges; clipping symmetrically in ``x`` leaves one end hanging short
    whenever the intercept is not zero.
    """
    candidates = [-edge, edge]
    if slope:
        candidates += [(-edge - intercept) / slope, (edge - intercept) / slope]

    inside = sorted(
        x
        for x in candidates
        if -edge - 1e-9 <= x <= edge + 1e-9 and -edge - 1e-9 <= slope * x + intercept <= edge + 1e-9
    )
    first, last = float(inside[0]), float(inside[-1])
    return (first, float(slope * first + intercept)), (last, float(slope * last + intercept))


# -- figures ---------------------------------------------------------------


def right_triangle(
    *,
    base: float,
    height: float,
    base_label: str,
    height_label: str,
    hypotenuse_label: str,
    unknown: str,
) -> str:
    """A right triangle with its three sides labelled.

    ``base`` and ``height`` set the drawn shape's proportions; the labels carry
    the numbers, so a scaled-up triple still looks like itself. ``unknown``
    names the side the question asks for, which is drawn in the accent colour.
    """
    span = 180 / max(base, height)
    width_px, height_px = base * span, height * span
    left, top = 58.0, 26.0
    bottom = top + height_px
    corner = (left, bottom)
    right = (left + width_px, bottom)
    apex = (left, top)

    parts = [
        polygon([corner, right, apex]),
        right_angle_mark(corner, right, apex),
        # Redraw the asked-for side on top of the outline so it reads as the subject.
        line(*corner, *right, color=ACCENT if unknown == "base" else INK),
        line(*corner, *apex, color=ACCENT if unknown == "height" else INK),
        line(*right, *apex, color=ACCENT if unknown == "hypotenuse" else INK),
        text(left + width_px / 2, bottom + 24, base_label, fill=ACCENT if unknown == "base" else INK,
             weight="600" if unknown == "base" else "400"),
        text(left - 12, top + height_px / 2 + 5, height_label, anchor="end",
             fill=ACCENT if unknown == "height" else INK,
             weight="600" if unknown == "height" else "400"),
        text(left + width_px / 2 + 20, top + height_px / 2 - 6, hypotenuse_label, anchor="start",
             fill=ACCENT if unknown == "hypotenuse" else INK,
             weight="600" if unknown == "hypotenuse" else "400"),
    ]
    described = {"base": base_label, "height": height_label, "hypotenuse": hypotenuse_label}
    label = (
        f"Right triangle. The legs are labeled {base_label} and {height_label}, and the "
        f"hypotenuse is labeled {hypotenuse_label}. The side labeled {described[unknown]} "
        "is the one in question."
    )
    return svg("".join(parts), width=left + width_px + 62, height=bottom + 38, label=label)


def crossing_lines(*, given: int, given_position: str, unknown_position: str, unknown_label: str = "x°") -> str:
    """Two straight lines crossing, one angle given and one asked for.

    Positions are ``"upper right"``, ``"upper left"``, ``"lower left"`` and
    ``"lower right"`` — the four angles around the intersection, drawn at the
    true measure so the picture agrees with the arithmetic.
    """
    center = (168.0, 116.0)
    reach = 132.0
    slant = given if given_position in ("upper right", "lower left") else 180 - given

    rays = {
        "east": 0.0,
        "west": 180.0,
        "slant up": float(slant),
        "slant down": float(slant - 180),
    }
    # Each corner angle is bounded by one ray of each line.
    corners = {
        "upper right": ("east", "slant up"),
        "upper left": ("slant up", "west"),
        "lower left": ("west", "slant down"),
        "lower right": ("slant down", "east"),
    }

    parts = [
        line(center[0] - reach, center[1], center[0] + reach, center[1]),
        line(
            center[0] - reach * math.cos(math.radians(slant)),
            center[1] + reach * math.sin(math.radians(slant)),
            center[0] + reach * math.cos(math.radians(slant)),
            center[1] - reach * math.sin(math.radians(slant)),
        ),
        f'<circle cx="{_n(center[0])}" cy="{_n(center[1])}" r="3.5" fill="{INK}"/>',
    ]

    for position, body, color in (
        (given_position, f"{given}°", MUTED),
        (unknown_position, unknown_label, ACCENT),
    ):
        first, second = corners[position]
        start, end = rays[first], rays[second]
        if end < start:
            end += 360
        radius = 34.0 if position == given_position else 44.0
        parts.append(angle_arc(center, start, end, radius, color=color))
        middle = math.radians((start + end) / 2)
        parts.append(
            text(
                center[0] + (radius + 16) * math.cos(middle),
                center[1] - (radius + 16) * math.sin(middle) + 5,
                body,
                fill=color,
                weight="600",
            )
        )

    label = (
        f"Two straight lines cross at a point, forming four angles. The {given_position} angle "
        f"measures {given} degrees. The {unknown_position} angle is labeled {unknown_label}."
    )
    return svg("".join(parts), width=336, height=232, label=label)


def labelled_triangle(*, angles: Sequence[int], labels: Sequence[str]) -> str:
    """A triangle whose three interior angles carry the given labels.

    The drawn shape uses the real angle measures, so a 100° angle looks obtuse
    and the picture never contradicts the arithmetic.
    """
    first, second = math.radians(angles[0]), math.radians(angles[1])
    # Place the base, then find the apex by intersecting the two base rays.
    base = 200.0
    height = base * math.tan(first) * math.tan(second) / (math.tan(first) + math.tan(second))
    apex_x = height / math.tan(first)

    left, top = 46.0, 30.0
    bottom = top + height
    corners = [(left, bottom), (left + base, bottom), (left + apex_x, top)]

    parts = [polygon(corners)]
    # Nudge each label inside the triangle, along the bisector from its corner.
    centroid = (sum(x for x, _ in corners) / 3, sum(y for _, y in corners) / 3)
    for corner, body in zip(corners, labels):
        dx, dy = _unit(centroid, corner)
        parts.append(
            text(corner[0] + dx * 42, corner[1] + dy * 42 + 5, body, size=13, weight="600", fill=ACCENT)
        )

    described = ", ".join(labels)
    label = f"Triangle with its three interior angles labeled {described}."
    return svg("".join(parts), width=left + base + 40, height=bottom + 34, label=label)


def bar_chart(*, categories: Sequence[str], values: Sequence[int], axis_title: str, title: str) -> str:
    """A vertical bar chart with a labelled value axis."""
    left, right_pad, top, bottom_pad = 54.0, 18.0, 34.0, 46.0
    bar_width, gap = 46.0, 26.0
    plot_height = 190.0

    top_tick, step = _axis_scale(max(values))
    width = left + len(values) * (bar_width + gap) + right_pad
    baseline = top + plot_height

    parts = [text(width / 2, 20, title, size=14, weight="600")]

    tick = 0
    while tick <= top_tick:
        y = baseline - plot_height * tick / top_tick
        parts.append(line(left, y, width - right_pad, y, color=GRID, width=1))
        parts.append(text(left - 10, y + 4, str(tick), size=12, anchor="end", fill=MUTED))
        tick += step

    for index, (name, value) in enumerate(zip(categories, values)):
        x = left + gap / 2 + index * (bar_width + gap)
        bar_height = plot_height * value / top_tick
        parts.append(
            f'<rect x="{_n(x)}" y="{_n(baseline - bar_height)}" width="{_n(bar_width)}" '
            f'height="{_n(bar_height)}" fill="{ACCENT}" rx="2"/>'
        )
        parts.append(text(x + bar_width / 2, baseline + 20, name, size=13))

    parts.append(line(left, baseline, width - right_pad, baseline, color=INK, width=2))
    parts.append(line(left, top - 8, left, baseline, color=INK, width=2))
    parts.append(
        f'<text x="16" y="{_n(top + plot_height / 2)}" {_FONT} font-size="12" fill="{MUTED}" '
        f'text-anchor="middle" transform="rotate(-90 16 {_n(top + plot_height / 2)})">'
        f"{html.escape(axis_title)}</text>"
    )

    readings = ", ".join(f"{name}, {value}" for name, value in zip(categories, values))
    label = (
        f"Bar graph titled {title}. The horizontal axis lists categories and the vertical axis "
        f"is labeled {axis_title}. The bars, in order, are: {readings}."
    )
    return svg("".join(parts), width=width, height=baseline + bottom_pad, label=label)


def rectangle(*, width_value: int, height_value: int, width_label: str, height_label: str) -> str:
    """A labelled rectangle."""
    span = 170 / max(width_value, height_value)
    w, h = width_value * span, height_value * span
    left, top = 52.0, 26.0

    parts = [
        f'<rect x="{_n(left)}" y="{_n(top)}" width="{_n(w)}" height="{_n(h)}" '
        f'fill="{WASH}" stroke="{INK}" stroke-width="2"/>',
        right_angle_mark((left, top + h), (left + w, top + h), (left, top)),
        text(left + w / 2, top + h + 24, width_label),
        text(left - 12, top + h / 2 + 5, height_label, anchor="end"),
    ]
    label = (
        f"Rectangle with its width labeled {width_label} and its height labeled {height_label}."
    )
    return svg("".join(parts), width=left + w + 30, height=top + h + 38, label=label)


def triangle(*, base_value: int, height_value: int, base_label: str, height_label: str) -> str:
    """A triangle with its base and its perpendicular height marked."""
    span = 170 / max(base_value, height_value)
    w, h = base_value * span, height_value * span
    left, top = 46.0, 26.0
    bottom = top + h
    apex_x = left + w * 0.38

    parts = [
        polygon([(left, bottom), (left + w, bottom), (apex_x, top)]),
        line(apex_x, top, apex_x, bottom, color=MUTED, width=1.5, dash="5 4"),
        right_angle_mark((apex_x, bottom), (left + w, bottom), (apex_x, top), size=11),
        text(left + w / 2, bottom + 24, base_label),
        # Just right of the dashed segment, so it cannot be read as labelling
        # the slanted side.
        text(apex_x + 10, top + h / 2 + 5, height_label, anchor="start", fill=MUTED),
    ]
    label = (
        f"Triangle with its base labeled {base_label}. A dashed segment from the opposite vertex "
        f"meets the base at a right angle and is labeled {height_label}."
    )
    return svg("".join(parts), width=left + w + 30, height=bottom + 38, label=label)


def prism(*, length: int, width_value: int, height_value: int, labels: tuple[str, str, str]) -> str:
    """A rectangular prism drawn in oblique projection, its three edges labelled."""
    span = 150 / max(length, width_value, height_value)
    w, h = length * span, height_value * span
    depth = width_value * span * 0.55
    left, top = 40.0, 30.0 + depth
    right, bottom = left + w, top + h

    parts = [
        polygon([(left, top), (right, top), (right, bottom), (left, bottom)], fill=WASH),
        polygon([(left, top), (left + depth, top - depth), (right + depth, top - depth), (right, top)], fill="#eff6ff"),
        polygon([(right, top), (right + depth, top - depth), (right + depth, bottom - depth), (right, bottom)], fill="#bfdbfe"),
        text((left + right) / 2, bottom + 24, labels[0]),
        # Below and right of the receding edge, clear of the shaded face.
        text(right + depth / 2 + 12, bottom - depth / 2 + 20, labels[1], anchor="start"),
        text(left - 12, (top + bottom) / 2 + 5, labels[2], anchor="end"),
    ]
    label = (
        f"Rectangular prism with edge lengths labeled {labels[0]}, {labels[1]} and {labels[2]}."
    )
    return svg("".join(parts), width=right + depth + 62, height=bottom + 38, label=label)


def _axis_scale(largest: int) -> tuple[int, int]:
    """A round top-of-axis value and tick step covering ``largest``."""
    for step in (1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000):
        top = math.ceil(largest / step) * step
        if top // step <= 6:
            return max(top, step), step
    return largest, max(largest // 5, 1)
