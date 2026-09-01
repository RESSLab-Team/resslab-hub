#!/usr/bin/env python3
"""Full export of an AISC sculpture .plt view, for manual cleaning.

Keeps everything (steel, dimensions, leaders, hidden lines, arrowheads,
bolts), only drops text labels and the tiny join-patch squares the plotter
puts on line ends. One <path> per segment so each line can be selected and
deleted in Inkscape/Illustrator. Content is split into Inkscape layers:
steel, annotations (hairline dims/leaders/arrowheads), fills (bolts and
other solid steel).

Text detection: a glyph is a small fill; letters in a word nearly touch
(bbox gap <= 8 units) while bolts are spaced apart, so clusters of small
fills that are not all round dots are words. Join patches are tiny 4-pt
squares whose center sits on a stroke endpoint.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plt2svg import Plot, extract_hpgl, parse
from cad2logo import VIEWS as LOGO_VIEWS

PLT_DIR = "./aisc-steel-sculpture-plans/Steel Sculpture Plans/Drawings - Plot Files"

VIEWS = {
    # ISO has almost no annotation: its hairlines are real steel (rods),
    # so it keeps everything in the steel layer.
    "iso": {"plt": "ISO.plt", "crop": (1700, 30, 8800, 5600), "no_split": True},
    "e2-section1": {
        "plt": "E2.plt",
        "crop": (1030, 450, 3820, 3590),
        # label zones in the margin the plate crop did not cover
        "extra": [
            (1830, 1400, 2040, 1560),  # 12A2 L3x3x3/8 widened
            (2700, 400, 3060, 520),    # top dim text
            (3600, 1200, 3821, 1340),  # 12K3 (NS) right edge
            (3600, 2380, 3821, 2560),  # 8B2 W12 (FS) right edge
            (2350, 3300, 2435, 3430),  # 1C1 W12x96 bottom widened
            (1095, 2935, 1140, 2990),  # 4/E2 bubble bits left edge
            (2840, 2675, 2930, 2745),  # 4B3 remnants
            (2975, 2815, 3020, 2855),  # 3/E2 remnants
            (2880, 3070, 2925, 3115),  # 5/E2 remnants
        ],
    },
    "e3-section6": {
        "plt": "E3.plt",
        "crop": (1230, 1060, 4020, 3940),
        "extra": [
            (2540, 2165, 2595, 2220),  # stray x mid column
            (2330, 3840, 3280, 3941),  # cropped section-title tops
        ],
    },
}


def quad_centerline(pts):
    a, b, c, d = pts[0], pts[1], pts[2], pts[3]

    def mid(p, q):
        return ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)

    def dist(p, q):
        return math.hypot(p[0] - q[0], p[1] - q[1])

    e = [dist(a, b), dist(b, c), dist(c, d), dist(d, a)]
    if min(e[0], e[2]) > 0 and max(e[1], e[3]) <= min(e[0], e[2]) * 0.55:
        return mid(d, a), mid(b, c), (e[1] + e[3]) / 2
    if min(e[1], e[3]) > 0 and max(e[0], e[2]) <= min(e[1], e[3]) * 0.55:
        return mid(a, b), mid(c, d), (e[0] + e[2]) / 2
    return None


def bbox(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def inside(bb, box):
    x0, y0, x1, y1 = bb
    return x0 >= box[0] and y0 >= box[1] and x1 <= box[2] and y1 <= box[3]


class Grid:
    """Coarse spatial hash for endpoint lookups."""

    def __init__(self, cell=32):
        self.cell = cell
        self.d = {}

    def add(self, p):
        k = (int(p[0] // self.cell), int(p[1] // self.cell))
        self.d.setdefault(k, []).append(p)

    def near(self, p, r):
        cx, cy = int(p[0] // self.cell), int(p[1] // self.cell)
        for kx in range(cx - 1, cx + 2):
            for ky in range(cy - 1, cy + 2):
                for q in self.d.get((kx, ky), ()):
                    if math.hypot(p[0] - q[0], p[1] - q[1]) <= r:
                        return True
        return False


def bb_gap(a, b):
    """Largest axis gap between two bboxes (0 if they overlap)."""
    dx = max(a[0] - b[2], b[0] - a[2], 0)
    dy = max(a[1] - b[3], b[1] - a[3], 0)
    return max(dx, dy)


def convert(view, out_path):
    cfg = VIEWS[view]
    data = open(f"{PLT_DIR}/{cfg['plt']}", "rb").read()
    plot = Plot()
    parse(extract_hpgl(data), plot)

    all_pts = [p for _, paths in plot.polygons for q in paths for p in q]
    gx0 = min(p[0] for p in all_pts)
    gy0 = min(p[1] for p in all_pts)

    def T(p):
        return (p[0] - gx0, p[1] - gy0)

    crop = cfg["crop"]
    logo = LOGO_VIEWS.get(view, {})
    boxes_hard = logo.get("exclude", []) + cfg.get("extra", [])
    boxes_soft = logo.get("smart", [])
    kill_segs = logo.get("kill_segs", [])
    kill_lines = logo.get("kill_lines", [])

    def killed_stroke(p, q):
        for kx0, ky0, kx1, ky1 in kill_segs:
            if (
                math.hypot(p[0] - kx0, p[1] - ky0) < 8
                and math.hypot(q[0] - kx1, q[1] - ky1) < 8
            ) or (
                math.hypot(p[0] - kx1, p[1] - ky1) < 8
                and math.hypot(q[0] - kx0, q[1] - ky0) < 8
            ):
                return True
        for lx0, ly0, lx1, ly1 in kill_lines:
            dx, dy = lx1 - lx0, ly1 - ly0
            L = math.hypot(dx, dy)
            ok = True
            for pt in (p, q):
                t = ((pt[0] - lx0) * dx + (pt[1] - ly0) * dy) / (L * L)
                dist = abs((pt[0] - lx0) * dy - (pt[1] - ly0) * dx) / L
                if not (-0.05 <= t <= 1.05 and dist <= 10):
                    ok = False
                    break
            if ok:
                return True
        return False

    steel = []
    annot = []
    small = []  # candidate fills: (bb, rings, roundish, triangle)
    big = []  # big solid fills, kept as-is
    n_text = 0
    text_bbs = []
    ends = Grid()
    for _pen, paths in plot.polygons:
        rings = [[T(p) for p in q] for q in paths if len(q) >= 3]
        if not rings:
            continue
        pts_all = [p for r in rings for p in r]
        bb = bbox(pts_all)
        if not inside(bb, crop):
            continue
        if len(rings) == 1 and len(rings[0]) == 5:
            cl = quad_centerline(rings[0])
            if cl:
                p, q, w = cl
                ln = math.hypot(p[0] - q[0], p[1] - q[1])
                if any(inside(bb, bx) for bx in boxes_hard):
                    continue  # known label zone
                if ln < 60 and any(inside(bb, bx) for bx in boxes_soft):
                    continue  # label drawn on top of steel
                if killed_stroke(p, q):
                    continue  # leader whose label is gone
                if w < 1.5 and not cfg.get("no_split"):
                    annot.append((p, q))
                else:
                    steel.append((p, q))
                ends.add(p)
                ends.add(q)
                continue
        w_ = bb[2] - bb[0]
        h_ = bb[3] - bb[1]
        md = max(w_, h_)
        if 75 <= md < 250 and h_ < 75:
            n_text += 1  # word block
            text_bbs.append(bb)
            continue
        if md < 75:
            roundish = (
                len(rings) == 1
                and len(rings[0]) >= 7
                and abs(w_ - h_) <= 4
                and md <= 22
            )
            if any(inside(bb, bx) for bx in boxes_hard) or (
                not roundish and any(inside(bb, bx) for bx in boxes_soft)
            ):
                n_text += 1  # inside a known label zone
                text_bbs.append(bb)
                continue
            quad = len(rings) == 1 and len(rings[0]) == 5
            small.append([bb, rings, roundish, quad])
        else:
            big.append(rings)

    # join patches: tiny squares (closed 4-pt rings) sitting on a stroke endpoint
    keep_small = []
    for item in small:
        bb, rings, roundish, quad = item
        md = max(bb[2] - bb[0], bb[3] - bb[1])
        c = ((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2)
        if quad and md <= 12 and ends.near(c, 6):
            continue  # join patch
        keep_small.append(item)

    # cluster remaining small fills into words (bbox gap <= 8)
    n = len(keep_small)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    cell = 64
    buckets = {}
    for i, item in enumerate(keep_small):
        bb = item[0]
        k = (int(bb[0] // cell), int(bb[1] // cell))
        buckets.setdefault(k, []).append(i)
    for i, item in enumerate(keep_small):
        bb = item[0]
        cx, cy = int(bb[0] // cell), int(bb[1] // cell)
        for kx in range(cx - 1, cx + 2):
            for ky in range(cy - 1, cy + 2):
                for j in buckets.get((kx, ky), ()):
                    if j <= i:
                        continue
                    if bb_gap(bb, keep_small[j][0]) <= 12:
                        ri, rj = find(i), find(j)
                        if ri != rj:
                            parent[rj] = ri
    clusters = {}
    for i in range(n):
        clusters.setdefault(find(i), []).append(i)

    arrows = []
    bolts = []  # (bb, rings, roundish) until the flood pass
    for members in clusters.values():
        items = [keep_small[i] for i in members]
        all_round = all(it[2] for it in items)
        big_member = max(
            max(it[0][2] - it[0][0], it[0][3] - it[0][1]) for it in items
        )
        n_dots = sum(
            1 for it in items if max(it[0][2] - it[0][0], it[0][3] - it[0][1]) <= 10
        )
        if (len(items) >= 2 and not all_round and big_member >= 25) or (
            len(items) >= 4
            and big_member <= 22
            and n_dots >= max(4, len(items) // 2)
        ):
            # word (letters are 25-45 units tall) or dotted-outline glyphs
            n_text += len(items)
            text_bbs.extend(it[0] for it in items)
            continue
        for bb, rings, roundish, quad in items:
            md = max(bb[2] - bb[0], bb[3] - bb[1])
            if roundish:
                bolts.append((bb, rings, True))
            elif len(rings) == 1 and len(rings[0]) <= 5 and md <= 30:
                arrows.append(rings)  # arrowheads, ticks, dashes
            elif md >= 23:
                n_text += 1  # lone letter
                text_bbs.append(bb)
            else:
                bolts.append((bb, rings, False))

    # stroke-drawn glyphs: cluster short hairline strokes; a dense small
    # cluster is a word. Bolt circles (square-ish, tiny) are protected.
    short_idx = []
    for i, (p, q) in enumerate(annot):
        ln = math.hypot(p[0] - q[0], p[1] - q[1])
        if ln < 45:
            sb = (min(p[0], q[0]), min(p[1], q[1]), max(p[0], q[0]), max(p[1], q[1]))
            short_idx.append((i, sb))
    ns = len(short_idx)
    sparent = list(range(ns))

    def sfind(i):
        while sparent[i] != i:
            sparent[i] = sparent[sparent[i]]
            i = sparent[i]
        return i

    sbuckets = {}
    for si, (_, sb) in enumerate(short_idx):
        k = (int(sb[0] // cell), int(sb[1] // cell))
        sbuckets.setdefault(k, []).append(si)
    for si, (_, sb) in enumerate(short_idx):
        cx, cy = int(sb[0] // cell), int(sb[1] // cell)
        for kx in range(cx - 1, cx + 2):
            for ky in range(cy - 1, cy + 2):
                for sj in sbuckets.get((kx, ky), ()):
                    if sj <= si:
                        continue
                    if bb_gap(sb, short_idx[sj][1]) <= 7:
                        ri, rj = sfind(si), sfind(sj)
                        if ri != rj:
                            sparent[rj] = ri
    sclusters = {}
    for si in range(ns):
        sclusters.setdefault(sfind(si), []).append(si)
    drop_annot = set()
    for members in sclusters.values():
        if len(members) < 4:
            continue
        bbs = [short_idx[si][1] for si in members]
        cb = (
            min(b[0] for b in bbs),
            min(b[1] for b in bbs),
            max(b[2] for b in bbs),
            max(b[3] for b in bbs),
        )
        cw, ch = cb[2] - cb[0], cb[3] - cb[1]
        cmd = max(cw, ch)
        circle_like = abs(cw - ch) <= 5 and cmd <= 26
        if cmd <= 350 and not circle_like:
            for si in members:
                drop_annot.add(short_idx[si][0])
            text_bbs.append(cb)
            n_text += len(members)

    # flood: leftover bits hanging next to dropped text are text too
    for _ in range(3):
        moved = False
        kept = []
        for bb, rings, roundish in bolts:
            tiny_dot = roundish and max(bb[2] - bb[0], bb[3] - bb[1]) <= 10
            if (not roundish or tiny_dot) and any(
                bb_gap(bb, tb) <= (12 if tiny_dot else 8) for tb in text_bbs
            ):
                n_text += 1
                text_bbs.append(bb)
                moved = True
            else:
                kept.append((bb, rings, roundish))
        bolts = kept
        for i, sb in short_idx:
            if i in drop_annot:
                continue
            sw, sh = sb[2] - sb[0], sb[3] - sb[1]
            if abs(sw - sh) <= 5 and max(sw, sh) <= 26:
                continue  # part of a bolt circle
            if any(bb_gap(sb, tb) <= 8 for tb in text_bbs):
                drop_annot.add(i)
                text_bbs.append(sb)
                n_text += 1
                moved = True
        if not moved:
            break
    bolts = [rings for _, rings, _ in bolts]
    annot = [s for i, s in enumerate(annot) if i not in drop_annot]

    x0, y0, x1, y1 = crop
    w, h = x1 - x0, y1 - y0
    pad = 40

    def fx(v):
        return round(v - x0 + pad, 1)

    def fy(v):
        return round(v - y0 + pad, 1)

    def seg_paths(segs):
        return "".join(
            f'<path d="M{fx(p[0])} {fy(p[1])}L{fx(q[0])} {fy(q[1])}"/>'
            for p, q in segs
        )

    def ring_paths(items):
        out = []
        for rings in items:
            d = "".join(
                f"M{fx(r[0][0])} {fy(r[0][1])}"
                + "".join(f"L{fx(x)} {fy(y)}" for x, y in r[1:])
                + "Z"
                for r in rings
            )
            out.append(f'<path d="{d}"/>')
        return "".join(out)

    NS = 'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"'
    LAYER = 'inkscape:groupmode="layer"'
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" {NS} viewBox="0 0 {w + 2 * pad:.0f} {h + 2 * pad:.0f}">',
        f'<g id="steel" {LAYER} inkscape:label="steel" fill="none" stroke="currentColor" '
        'stroke-width="7" stroke-linecap="round" stroke-linejoin="round">',
        seg_paths(steel),
        "</g>",
        f'<g id="annotations" {LAYER} inkscape:label="annotations" opacity="0.5">',
        '<g fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">',
        seg_paths(annot),
        '</g><g fill="currentColor" stroke="none">',
        ring_paths(arrows),
        "</g></g>",
        f'<g id="fills" {LAYER} inkscape:label="fills" fill="currentColor" stroke="none" fill-rule="evenodd">',
        ring_paths(bolts + big),
        "</g></svg>",
    ]
    with open(out_path, "w") as f:
        f.write("\n".join(parts))
    print(
        f"{view}: {len(steel)} steel, {len(annot)} annot, {len(arrows)} arrows, "
        f"{len(bolts) + len(big)} fills, {n_text} text dropped -> {out_path}"
    )


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])
