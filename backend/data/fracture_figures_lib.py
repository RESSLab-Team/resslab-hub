"""Drawings of ductile-fracture specimen geometries.

Ported from ``Process_fracture_figures.ipynb`` (A. Skiadopoulos, issue #238):
a circumferentially notched tensile bar (CNT) and a grooved plate (GP) drawn
to scale from their nominal dimensions, with the notch dimensions annotated.

The notebook typesets its labels through LaTeX (``text.usetex``). Requiring a
TeX installation to regenerate the figures is not worth it, so matplotlib's own
mathtext does the job here with a Times-compatible serif face.
"""

from __future__ import annotations

import io
from typing import Mapping

import matplotlib

matplotlib.use("Agg")

import numpy as np  # noqa: E402
from matplotlib import rc_context  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.patches import Ellipse, Polygon  # noqa: E402

# Nominal dimensions each geometry is drawn from, in call order.
SPECIMEN_COLUMNS = {
    "CNT": (
        "gauge_length",
        "nom_notch_radius",
        "nom_whole_diameter_cnt",
        "nom_notch_diameter_cnt",
    ),
    "GP": (
        "gauge_length",
        "nom_notch_radius",
        "nom_width_gp",
        "nom_whole_thickness_gp",
        "nom_notch_thickness_gp",
    ),
}

LINE_COLOR = "0.08"
BODY_COLOR = "#e9eef2"
CAP_COLOR = "#f8fafc"
SIDE_COLOR = "#d7dee5"
CONSTRUCTION_COLOR = "0.45"

RC_PARAMS = {
    "text.usetex": False,
    "font.family": "serif",
    "font.serif": [
        "Times New Roman",
        "Liberation Serif",
        "Nimbus Roman",
        "DejaVu Serif",
    ],
    "mathtext.fontset": "stix",
    "axes.linewidth": 0.4,
    "figure.max_open_warning": 0,
    "svg.fonttype": "path",  # no font lookup in the browser
    # These SVGs are committed, so rerunning the script over unchanged data has
    # to produce byte-identical files. A fixed salt pins the clip-path ids that
    # matplotlib otherwise derives from a random uuid; the timestamp is dropped
    # at savefig time.
    "svg.hashsalt": "resslab-hub-ductile-fracture",
}

ARROW_PROPS = dict(
    arrowstyle="<->", color=LINE_COLOR, linewidth=1.1, shrinkA=0, shrinkB=0
)
RADIUS_ARROW_PROPS = dict(
    arrowstyle="->", color=LINE_COLOR, linewidth=1.1, shrinkA=0, shrinkB=0
)
LABEL_BOX = dict(
    boxstyle="round,pad=0.15", facecolor="white", edgecolor="none", alpha=0.85
)

# Segments per notch fillet. The notebook uses 120; at the size these figures
# are ever shown 48 is indistinguishable (0.2% of pixels differ at 300 dpi) and
# a third off the SVG, which matters for 100-odd committed files.
ARC_POINTS = 48


def _notch_arcs(notch_radius: float, notch_depth: float, core_half: float):
    """Fillet arcs on either side of the notch, and the half-height they span.

    A notch shallower than the tool radius only sweeps part of the arc, so the
    sweep angle comes from how deep the cut actually is.
    """
    if notch_radius <= 0 or notch_depth <= 0:
        theta = 0.0
        notch_half_width = 0.0
    elif notch_radius < notch_depth:
        theta = np.pi / 2
        notch_half_width = notch_radius
    else:
        theta = np.arccos(np.clip((notch_radius - notch_depth) / notch_radius, -1, 1))
        notch_half_width = notch_radius * np.sin(theta)

    right_center_x = core_half + notch_radius
    left_center_x = -core_half - notch_radius
    right_phi = np.linspace(theta, -theta, ARC_POINTS)
    left_phi = np.linspace(-theta, theta, ARC_POINTS)
    right_curve = np.column_stack(
        (
            right_center_x - notch_radius * np.cos(right_phi),
            notch_radius * np.sin(right_phi),
        )
    )
    left_curve = np.column_stack(
        (
            left_center_x + notch_radius * np.cos(left_phi),
            notch_radius * np.sin(left_phi),
        )
    )
    return right_curve, left_curve, notch_half_width


def _notched_outline(
    body_half, gauge_length, right_curve, left_curve, notch_half_width
):
    """Silhouette of a notched bar: straight flanks joined by the two arcs."""
    return [
        (-body_half, gauge_length / 2),
        (body_half, gauge_length / 2),
        (body_half, notch_half_width),
        *right_curve.tolist(),
        (body_half, -notch_half_width),
        (body_half, -gauge_length / 2),
        (-body_half, -gauge_length / 2),
        (-body_half, -notch_half_width),
        *left_curve.tolist(),
        (-body_half, notch_half_width),
    ]


def _cross_2d(a, b) -> float:
    return a[0] * b[1] - a[1] * b[0]


def draw_cnt_specimen(
    gauge_length: float,
    notch_radius: float,
    unnotched_diameter: float,
    notched_diameter: float,
) -> Figure:
    """Circumferentially notched tensile bar, seen from the side."""
    gauge_length = float(gauge_length)
    notch_radius = float(notch_radius)
    unnotched_diameter = float(unnotched_diameter)
    notched_diameter = float(notched_diameter)

    figure = Figure(figsize=(6.4, 4.0))
    ax = figure.add_subplot()

    cap_height = 0.22 * unnotched_diameter
    notch_depth = (unnotched_diameter - notched_diameter) / 2
    right_curve, left_curve, notch_half_width = _notch_arcs(
        notch_radius, notch_depth, notched_diameter / 2
    )
    outline = _notched_outline(
        unnotched_diameter / 2, gauge_length, right_curve, left_curve, notch_half_width
    )

    # Ellipse caps top and bottom read the round bar as a cylinder; the far one
    # sits under the body so only its back half shows.
    ax.add_patch(
        Ellipse(
            (0, -gauge_length / 2),
            unnotched_diameter,
            cap_height,
            facecolor=CAP_COLOR,
            edgecolor=LINE_COLOR,
            linewidth=1.6,
            zorder=1,
        )
    )
    ax.add_patch(
        Polygon(
            outline,
            closed=True,
            facecolor=BODY_COLOR,
            edgecolor=LINE_COLOR,
            linewidth=1.8,
            zorder=2,
        )
    )
    ax.add_patch(
        Ellipse(
            (0, gauge_length / 2),
            unnotched_diameter,
            cap_height,
            facecolor=CAP_COLOR,
            edgecolor=LINE_COLOR,
            linewidth=1.8,
            zorder=3,
        )
    )
    ax.plot(
        [-unnotched_diameter / 2, unnotched_diameter / 2],
        [gauge_length / 2, gauge_length / 2],
        color="white",
        linewidth=1.0,
        alpha=0.65,
        zorder=4,
    )
    ax.plot(
        [0, 0],
        [-gauge_length / 2, gauge_length / 2],
        color="white",
        linewidth=1.0,
        alpha=0.55,
        zorder=4,
    )

    top_dim_y = gauge_length / 2 + 1.15 * cap_height
    ax.annotate(
        "",
        xy=(-unnotched_diameter / 2, top_dim_y),
        xytext=(unnotched_diameter / 2, top_dim_y),
        arrowprops=ARROW_PROPS,
    )
    for x in (-unnotched_diameter / 2, unnotched_diameter / 2):
        ax.plot(
            [x, x],
            [gauge_length / 2, top_dim_y],
            color=CONSTRUCTION_COLOR,
            linewidth=0.8,
        )
    ax.text(
        0,
        top_dim_y + 0.04 * gauge_length,
        f"$D_{{UN}}$ = {unnotched_diameter:g}",
        ha="center",
        va="bottom",
        fontsize=11,
        bbox=LABEL_BOX,
    )

    ax.annotate(
        "",
        xy=(-notched_diameter / 2, 0),
        xytext=(notched_diameter / 2, 0),
        arrowprops=ARROW_PROPS,
        zorder=5,
    )
    ax.text(
        0,
        -0.08 * gauge_length,
        f"$D_N$ = {notched_diameter:g}",
        ha="center",
        va="top",
        fontsize=11,
        bbox=LABEL_BOX,
        zorder=6,
    )

    if notch_radius > 0 and notch_depth > 0:
        tail_x = notched_diameter / 2 + unnotched_diameter / 2
        ax.annotate(
            "",
            xy=(notched_diameter / 2, 0),
            xytext=(tail_x, 0),
            arrowprops=RADIUS_ARROW_PROPS,
            zorder=5,
        )
        ax.text(
            (tail_x + notched_diameter / 2) / 2,
            0.08 * gauge_length,
            f"$R_N$ = {notch_radius:g}",
            ha="center",
            va="bottom",
            fontsize=11,
            bbox=LABEL_BOX,
            zorder=6,
        )

    x_margin = 0.30 * unnotched_diameter
    x_min = -unnotched_diameter / 2 - x_margin
    x_max = max(
        unnotched_diameter / 2 + x_margin,
        notched_diameter / 2 + 0.75 * unnotched_diameter,
    )
    y_margin = 0.16 * gauge_length
    ax.text(
        x_min,
        -gauge_length / 2 - 0.08 * gauge_length,
        "unit: mm",
        ha="left",
        va="top",
        fontsize=10,
    )

    ax.set_xlim(x_min, x_max)
    ax.set_ylim(-gauge_length / 2 - y_margin, top_dim_y + 0.15 * gauge_length)
    ax.set_aspect("equal")
    ax.axis("off")
    return figure


def draw_gp_specimen(
    gauge_length: float,
    notch_radius: float,
    width: float,
    unnotched_thickness: float,
    notched_thickness: float,
) -> Figure:
    """Grooved plate, drawn in oblique projection so the width reads too."""
    gauge_length = float(gauge_length)
    notch_radius = float(notch_radius)
    width = float(width)
    unnotched_thickness = float(unnotched_thickness)
    notched_thickness = float(notched_thickness)

    figure = Figure(figsize=(7.0, 4.0))
    ax = figure.add_subplot()

    notch_depth = (unnotched_thickness - notched_thickness) / 2
    right_curve, left_curve, notch_half_width = _notch_arcs(
        notch_radius, notch_depth, notched_thickness / 2
    )
    front_outline = _notched_outline(
        unnotched_thickness / 2, gauge_length, right_curve, left_curve, notch_half_width
    )

    # Oblique offset standing in for the plate width.
    depth_dx = 0.22 * width
    depth_dy = 0.10 * width
    offset = np.array([depth_dx, depth_dy])
    back_outline = [(x + depth_dx, y + depth_dy) for x, y in front_outline]

    front_top_left = (-unnotched_thickness / 2, gauge_length / 2)
    front_top_right = (unnotched_thickness / 2, gauge_length / 2)
    front_bottom_right = (unnotched_thickness / 2, -gauge_length / 2)
    front_bottom_left = (-unnotched_thickness / 2, -gauge_length / 2)
    front_right_upper = (unnotched_thickness / 2, notch_half_width)
    front_right_lower = (unnotched_thickness / 2, -notch_half_width)
    front_left_lower = (-unnotched_thickness / 2, -notch_half_width)
    front_left_upper = (-unnotched_thickness / 2, notch_half_width)

    def shifted(point):
        return (point[0] + depth_dx, point[1] + depth_dy)

    back_top_left = shifted(front_top_left)
    back_top_right = shifted(front_top_right)
    back_bottom_right = shifted(front_bottom_right)
    back_bottom_left = shifted(front_bottom_left)
    back_right_upper = shifted(front_right_upper)
    back_right_lower = shifted(front_right_lower)
    back_left_lower = shifted(front_left_lower)
    back_left_upper = shifted(front_left_upper)
    back_right_curve = right_curve + offset
    back_left_curve = left_curve + offset

    ax.add_patch(
        Polygon(
            back_outline,
            closed=True,
            facecolor=SIDE_COLOR,
            edgecolor="none",
            linewidth=0,
            zorder=1,
        )
    )
    ax.add_patch(
        Polygon(
            [front_top_left, front_top_right, back_top_right, back_top_left],
            closed=True,
            facecolor=SIDE_COLOR,
            edgecolor=LINE_COLOR,
            linewidth=1.4,
            zorder=2,
        )
    )
    ax.add_patch(
        Polygon(
            [
                front_bottom_left,
                front_bottom_right,
                back_bottom_right,
                back_bottom_left,
            ],
            closed=True,
            facecolor=SIDE_COLOR,
            edgecolor="none",
            linewidth=0,
            zorder=2,
        )
    )
    ax.plot(
        [front_bottom_right[0], back_bottom_right[0]],
        [front_bottom_right[1], back_bottom_right[1]],
        color=LINE_COLOR,
        linewidth=1.4,
        zorder=4,
    )
    ax.add_patch(
        Polygon(
            [front_right_upper, front_top_right, back_top_right, back_right_upper],
            closed=True,
            facecolor=SIDE_COLOR,
            edgecolor=LINE_COLOR,
            linewidth=1.2,
            zorder=2,
        )
    )
    ax.add_patch(
        Polygon(
            [
                front_right_lower,
                front_bottom_right,
                back_bottom_right,
                back_right_lower,
            ],
            closed=True,
            facecolor=SIDE_COLOR,
            edgecolor=LINE_COLOR,
            linewidth=1.2,
            zorder=2,
        )
    )
    # The left flank faces away, so it is filled but only selectively outlined.
    ax.add_patch(
        Polygon(
            [front_left_upper, front_top_left, back_top_left, back_left_upper],
            closed=True,
            facecolor=SIDE_COLOR,
            edgecolor="none",
            linewidth=0,
            zorder=2,
        )
    )
    ax.plot(
        [front_left_upper[0], front_top_left[0]],
        [front_left_upper[1], front_top_left[1]],
        color=LINE_COLOR,
        linewidth=1.2,
        zorder=4,
    )
    ax.plot(
        [front_top_left[0], back_top_left[0]],
        [front_top_left[1], back_top_left[1]],
        color=LINE_COLOR,
        linewidth=1.2,
        zorder=4,
    )
    ax.add_patch(
        Polygon(
            [front_left_lower, front_bottom_left, back_bottom_left, back_left_lower],
            closed=True,
            facecolor=SIDE_COLOR,
            edgecolor="none",
            linewidth=0,
            zorder=2,
        )
    )
    ax.plot(
        [front_left_lower[0], front_bottom_left[0]],
        [front_left_lower[1], front_bottom_left[1]],
        color=LINE_COLOR,
        linewidth=1.2,
        zorder=4,
    )
    # Swept groove surface: the ribbon each arc traces as it is extruded along
    # the offset. The notebook fills it one quad per arc segment; a single
    # untraced polygon per arc paints the same area for a hundredth of the SVG.
    for curve, back_curve in (
        (right_curve, back_right_curve),
        (left_curve, back_left_curve),
    ):
        ax.add_patch(
            Polygon(
                [*curve.tolist(), *back_curve[::-1].tolist()],
                closed=True,
                facecolor=SIDE_COLOR,
                edgecolor="none",
                zorder=2.5,
            )
        )

    # Hidden-line removal for the far groove edge: draw it only from where it
    # emerges past the near solid, otherwise it reads as a line through the body.
    solid_clip_segments = [
        (np.array(front_right_upper), np.array(back_right_upper)),
        (np.array(front_right_lower), np.array(back_right_lower)),
        (np.array(front_top_right), np.array(back_top_right)),
        (np.array(front_bottom_right), np.array(back_bottom_right)),
    ]
    back_right_curve_visible = []
    for index in range(len(back_right_curve) - 1):
        segment_start = back_right_curve[index]
        segment_direction = back_right_curve[index + 1] - segment_start
        best_intersection = None
        for clip_start, clip_end in solid_clip_segments:
            clip_direction = clip_end - clip_start
            denominator = _cross_2d(segment_direction, clip_direction)
            if abs(denominator) < 1e-12:
                continue
            gap = clip_start - segment_start
            curve_scale = _cross_2d(gap, clip_direction) / denominator
            clip_scale = _cross_2d(gap, segment_direction) / denominator
            if 0 <= curve_scale <= 1 and 0 <= clip_scale <= 1:
                point = segment_start + curve_scale * segment_direction
                if best_intersection is None or curve_scale < best_intersection[0]:
                    best_intersection = (curve_scale, point)
        if best_intersection is not None:
            back_right_curve_visible = [
                best_intersection[1],
                *back_right_curve[index + 1 :].tolist(),
            ]
            break
    if len(back_right_curve_visible) > 1:
        visible = np.array(back_right_curve_visible)
        ax.plot(visible[:, 0], visible[:, 1], color=LINE_COLOR, linewidth=1.0, zorder=4)
        ax.plot(
            [back_right_curve[-1, 0], back_right_lower[0]],
            [back_right_curve[-1, 1], back_right_lower[1]],
            color=LINE_COLOR,
            linewidth=1.0,
            zorder=4,
        )

    ax.add_patch(
        Polygon(
            front_outline,
            closed=True,
            facecolor=BODY_COLOR,
            edgecolor=LINE_COLOR,
            linewidth=1.8,
            zorder=3,
        )
    )
    ax.plot(
        [front_left_lower[0], left_curve[0, 0]],
        [front_left_lower[1], left_curve[0, 1]],
        color=LINE_COLOR,
        linewidth=1.8,
        solid_capstyle="butt",
        zorder=8,
    )

    # Width edge at the lower-left corner, stopped where it meets the groove.
    width_edge_start = np.array(front_left_lower)
    width_edge_end = np.array(back_left_lower)
    intersections = []
    for index in range(len(left_curve) - 1):
        curve_start = left_curve[index]
        curve_direction = left_curve[index + 1] - curve_start
        denominator = _cross_2d(offset, curve_direction)
        if abs(denominator) < 1e-12:
            continue
        gap = curve_start - width_edge_start
        line_scale = _cross_2d(gap, curve_direction) / denominator
        curve_scale = _cross_2d(gap, offset) / denominator
        if 0 <= line_scale <= 1 and 0 <= curve_scale <= 1:
            intersections.append((line_scale, width_edge_start + line_scale * offset))
    if intersections:
        _, width_edge_end = min(intersections, key=lambda item: item[0])
    ax.plot(
        [width_edge_start[0], width_edge_end[0]],
        [width_edge_start[1], width_edge_end[1]],
        color=LINE_COLOR,
        linewidth=1.2,
        zorder=6,
    )
    ax.plot(
        [0, 0],
        [-gauge_length / 2, gauge_length / 2],
        color="white",
        linewidth=1.0,
        alpha=0.55,
        zorder=4,
    )

    top_dim_y = gauge_length / 2 + 0.16 * gauge_length
    ax.annotate(
        "",
        xy=(-unnotched_thickness / 2, top_dim_y),
        xytext=(unnotched_thickness / 2, top_dim_y),
        arrowprops=ARROW_PROPS,
    )
    for x in (-unnotched_thickness / 2, unnotched_thickness / 2):
        ax.plot(
            [x, x],
            [gauge_length / 2, top_dim_y],
            color=CONSTRUCTION_COLOR,
            linewidth=0.8,
        )
    ax.text(
        0,
        top_dim_y + 0.04 * gauge_length,
        f"$T_{{UN}}$ = {unnotched_thickness:g}",
        ha="center",
        va="bottom",
        fontsize=11,
        bbox=LABEL_BOX,
    )

    ax.annotate(
        "",
        xy=(-notched_thickness / 2, 0),
        xytext=(notched_thickness / 2, 0),
        arrowprops=ARROW_PROPS,
        zorder=5,
    )
    ax.text(
        -0.12 * unnotched_thickness,
        -0.14 * gauge_length,
        f"$T_N$ = {notched_thickness:g}",
        ha="center",
        va="top",
        fontsize=11,
        bbox=LABEL_BOX,
        zorder=6,
    )

    if notch_radius > 0 and notch_depth > 0:
        tail_x = notched_thickness / 2 + unnotched_thickness / 2
        ax.annotate(
            "",
            xy=(notched_thickness / 2, 0),
            xytext=(tail_x, 0),
            arrowprops=RADIUS_ARROW_PROPS,
            zorder=5,
        )
        ax.text(
            (tail_x + notched_thickness / 2) / 2,
            0.08 * gauge_length,
            f"$R_N$ = {notch_radius:g}",
            ha="center",
            va="bottom",
            fontsize=11,
            bbox=LABEL_BOX,
            zorder=6,
        )

    width_dim_y = -gauge_length / 2 - 0.045 * gauge_length
    width_dim_start = (front_bottom_right[0] + 0.08 * unnotched_thickness, width_dim_y)
    width_dim_end = (width_dim_start[0] + depth_dx, width_dim_start[1] + depth_dy)
    ax.annotate("", xy=width_dim_start, xytext=width_dim_end, arrowprops=ARROW_PROPS)
    ax.text(
        (width_dim_start[0] + width_dim_end[0]) / 2,
        (width_dim_start[1] + width_dim_end[1]) / 2 - 0.075 * gauge_length,
        f"$W$ = {width:g}",
        ha="center",
        va="top",
        fontsize=11,
        bbox=LABEL_BOX,
    )

    x_margin = 0.30 * unnotched_thickness
    x_min = -unnotched_thickness / 2 - x_margin
    x_max = unnotched_thickness / 2 + depth_dx + x_margin
    y_margin = 0.22 * gauge_length
    ax.text(
        x_min,
        -gauge_length / 2 - 0.13 * gauge_length,
        "unit: mm",
        ha="left",
        va="top",
        fontsize=10,
    )

    ax.set_xlim(x_min, x_max)
    ax.set_ylim(
        -gauge_length / 2 - y_margin, top_dim_y + depth_dy + 0.15 * gauge_length
    )
    ax.set_aspect("equal")
    ax.axis("off")
    return figure


DRAW_FUNCTIONS = {"CNT": draw_cnt_specimen, "GP": draw_gp_specimen}


def render_specimen_svg(row: Mapping[str, str]) -> str:
    """SVG drawing for one ``ductile_fracture.csv`` row.

    Raises ``ValueError`` when the row carries an unknown specimen type or
    lacks a dimension the drawing needs (the CSV writes those as "NA").
    """
    specimen_type = (row.get("specimen_type") or "").strip()
    columns = SPECIMEN_COLUMNS.get(specimen_type)
    if columns is None:
        raise ValueError(f"unknown specimen_type {specimen_type!r}")

    dimensions = []
    for column in columns:
        raw = (row.get(column) or "").strip()
        try:
            dimensions.append(float(raw))
        except ValueError:
            raise ValueError(f"{column} is not a number: {raw!r}") from None

    with rc_context(RC_PARAMS):
        figure = DRAW_FUNCTIONS[specimen_type](*dimensions)
        buffer = io.BytesIO()
        figure.savefig(
            buffer, format="svg", bbox_inches="tight", metadata={"Date": None}
        )
    return buffer.getvalue().decode("utf-8")
