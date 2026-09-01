#!/usr/bin/env python3
"""Turn a decoded AISC sculpture .plt into a clean line-work SVG.

Quads (5-pt closed polygons) become centerline strokes; bigger polygons
(glyphs, bolt heads, arrowheads) become fills. A crop box keeps only the
drawing; exclusion boxes remove leftover callouts inside it.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plt2svg import Plot, extract_hpgl, parse

PLT_DIR = "./aisc-steel-sculpture-plans/Steel Sculpture Plans/Drawings - Plot Files"

# crop/exclude in decoded units, y from top, full sheet is 10576x6768
VIEWS = {
    "iso": {
        "plt": "ISO.plt",
        "crop": (1700, 30, 8800, 5600),
        "exclude": [],
    },
    "e2-section1": {
        "plt": "E2.plt",
        "crop": (1150, 570, 3700, 3470),
        "exclude": [
            (1330, 615, 1700, 740),   # deck note
            (1140, 810, 1395, 925),   # C8/10B4 left
            (1285, 1015, 1395, 1080), # 13T1
            (2110, 950, 2330, 1070),  # C8/10B4 mid
            (2090, 1150, 2240, 1210), # WT4x12
            (1845, 1415, 2030, 1520), # 12A2 L3x3
            (3580, 1250, 3700, 1350), # 12K3 right
            (3140, 1195, 3335, 1350), # 9B2
            (2645, 1372, 2740, 1420), # 5B3
            (2680, 1828, 2775, 1965), # 3C1 W10x33
            (3135, 1898, 3380, 2035), # 7B2
            (1150, 2160, 1425, 2262), # 4B2 left
            (1795, 2188, 1870, 2245), # 4B1
            (2172, 2652, 2276, 2815), # 2C1 W12x53
            (2812, 2688, 2888, 2745), # 4B3
            (2905, 2730, 3030, 2835), # bubble 3/E2
            (2812, 2968, 2930, 3078), # bubble 5/E2
            (1462, 2852, 1572, 2930), # 11D1
            (1882, 3292, 1950, 3368), # 8 + arrow
            (2365, 3082, 2448, 3378), # 1C1 W12x96
            (1150, 3340, 1230, 3470), # stray arrow left
            (2418, 540, 3100, 615),   # top dim line
            (2415, 565, 2470, 940),   # top centerline stub
            (2995, 565, 3030, 935),   # top dim ext right
            (1850, 3250, 1920, 3375), # 8-dim arrow
            (2749, 875, 2865, 925),   # 12K3 text top
            (1855, 1495, 1945, 1545), # 12A2 glyph dots
            (1600, 620, 1740, 690),   # top-left dash
            (2950, 1320, 2990, 1355), # 12K3 arrow bit
            (2880, 3040, 2925, 3085), # stray 9
        ],
        "smart": [
            (2510, 2458, 2642, 2510), # 4B3 mid ghost
            (3130, 1360, 3300, 1415), # W16x36 right text over flange
            (2035, 2215, 2185, 2292), # 16x36 mid text over flange
            (3455, 2670, 3630, 2725), # 16x36 bottom right text
            (1855, 2180, 1900, 2220), # M ghost
            (1270, 2880, 1370, 2975), # 4/E2 arrow remnant
            (2570, 2140, 3120, 3300), # callout ovals bottom right
            (1780, 2985, 2100, 3175), # HSS4x4 text on brace
            (1210, 1000, 1310, 1060), # stray paren + comma
            (1990, 1505, 2030, 1545), # stray c
            (2640, 1950, 2730, 2020), # ghost mid column
            (2690, 1905, 2750, 1940), # tick right of column
            (1630, 760, 1700, 880),   # deck leader arrowhead
            (2385, 3320, 2465, 3395), # M ghost bottom
            (2370, 3315, 2435, 3410), # bottom bits
            (3125, 2220, 3215, 2295), # arrow right beam
            (1110, 2800, 1235, 3100), # left edge bits
        ],
        "kill_segs": [
            (3020, 588, 3020, 1657), # long dim ext line
        ],
        "kill_lines": [
            (1715, 846, 2214, 1258),  # deck note leader
            (2020, 1455, 2320, 1350), # 12A2 leader
            (3030, 1336, 3074, 1368), # arrow hook W10x19
            (3416, 1350, 3468, 1380), # arrow hook 12K3
            (1720, 635, 1645, 870),   # deck leader top
            (3640, 1272, 3543, 1358), # 12K3 leader right
            (3144, 1915, 3156, 2292), # 7B2 leader
            (2760, 2727, 2965, 2727), # 4B3 leader stub
            (2767, 2731, 2863, 2810), # 3/E2 arrow diag2
            (2715, 2943, 2990, 2943), # 5/E2 leader stub
            (2434, 570, 2434, 700),   # top center dim stub
            (1868, 3006, 1941, 3046), # brace leader stub
            (2960, 2860, 3070, 2950), # 5/E2 arrow diag
        ],
        "min_width": 1.5,
        "drop_glyphs": True,
    },
    "e3-section6": {
        "plt": "E3.plt",
        "crop": (1350, 1180, 3900, 3820),
        "exclude": [
            (1540, 1490, 1730, 1585), # 12K3 (NS) left
            (1940, 1440, 2140, 1600), # 9B2 10x19
            (1440, 1905, 1700, 2020), # 10B3 C9x13.4
            (1890, 2140, 2090, 2292), # 7B2 W16x26
            (2490, 2195, 2615, 2288), # 3C1 W10x33
            (2335, 2340, 2510, 2455), # 2-3P2 shims
            (1395, 2630, 1555, 2790), # 8B2 12x26 FS
            (2480, 2950, 2620, 3122), # 2C1 12x53
            (2335, 3215, 2510, 3330), # 2-3P1 shims
            (2800, 3255, 2865, 3372), # W12x96 label
            (2755, 3555, 2830, 3615), # 1C1
            (3312, 3480, 3368, 3595), # 8 dim arrow
            (2941, 1220, 3155, 1310), # C8 10B4 top right
            (3805, 1210, 3900, 1340), # 2" deck note corner
            (2595, 1180, 2700, 1215), # 12K3 top
            (2540, 2118, 2602, 2192), # 10x33 upper
            (1450, 1975, 1485, 2012), # stray paren left
            (3860, 1230, 3900, 1300), # right edge bits
        ],
        "smart": [
            (2510, 2458, 2642, 2510), # 4B3 mid ghost
            (2020, 1620, 2165, 1672), # 16x36
            (2520, 1632, 2645, 1675), # 5B3
            (2185, 2470, 2325, 2515), # 16x36 left
            (2698, 2475, 2772, 2512), # 4B3
            (3095, 2470, 3240, 2515), # 16x36 right
            (3370, 2435, 3475, 2488), # 4B1
            (3110, 3172, 3355, 3340), # HSS text on brace
            (3320, 1395, 3440, 1440), # WT4x12
        ],
        "kill_segs": [
            (1681.5, 1941, 1920.5, 1757), # 10B3 leader
            (1673.5, 1522, 1824.5, 1612), # 12K3 arrow line
            (1824.5, 1612, 1804.5, 1605), # arrow barb 1
            (1809.5, 1597, 1824.5, 1612), # arrow barb 2
            (2062, 2164, 2112, 2164),     # 7B2 leader h
            (2112, 2164, 2096, 2522),     # 7B2 leader v
            (3388.5, 1216.5, 3332.5, 1226.5), # C8 arrow 1
            (3334, 1231.5, 3376, 1231.5),     # C8 arrow 2
            (3145, 1287, 3385, 1250),         # C8 leader
        ],
        "kill_lines": [
            (1757, 1512, 1815, 1610), # 12K3 arrow
            (1661, 1955, 1871, 1771), # 10B3 leader
            (2099, 2160, 2108, 2495), # 7B2 leader
            (2502, 2367, 2634, 2288), # shims leader up
            (1550, 2652, 1840, 2652), # 8B2 leader
            (2495, 3230, 2645, 3118), # shims leader bottom
            (3151, 1236, 3361, 1250), # C8 leader
            (3826, 1272, 3809, 1333), # deck note leader
            (3396, 1249, 2976, 1535), # long deck diagonal
            (1661, 1512, 1810, 1610), # 12K3 arrow full
            (2516, 2367, 2630, 2290), # shims leader dup
            (2516, 3311, 2630, 3209), # bottom shims leader dup
            (3204, 1205, 3204, 1270), # deck note vertical
        ],
        "min_width": 1.5,
        "drop_glyphs": True,
    },
}


def quad_centerline(pts):
    """pts: closed ring (first==last, 5 entries). Return (p, q, width) or None."""
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


def overlaps(bb, box):
    x0, y0, x1, y1 = bb
    return not (x1 < box[0] or x0 > box[2] or y1 < box[1] or y0 > box[3])


def convert(view, out_path, stroke=7.0, min_seg=0.0):
    cfg = VIEWS[view]
    data = open(f"{PLT_DIR}/{cfg['plt']}", "rb").read()
    plot = Plot()
    parse(extract_hpgl(data), plot)

    # decoded raw coords: x right, y down already (empirically)
    all_pts = [p for _, paths in plot.polygons for q in paths for p in q]
    gx0 = min(p[0] for p in all_pts)
    gy0 = min(p[1] for p in all_pts)

    def T(p):
        return (p[0] - gx0, p[1] - gy0)

    crop = cfg["crop"]
    segs = []  # (p,q)
    fills = []  # list of rings
    n_txt = 0
    for _pen, paths in plot.polygons:
        rings = [[T(p) for p in q] for q in paths if len(q) >= 3]
        if not rings:
            continue
        pts_all = [p for r in rings for p in r]
        bb = bbox(pts_all)
        if not inside(bb, crop):
            continue
        if any(inside(bb, ex) for ex in cfg["exclude"]):
            continue
        if len(rings) == 1 and len(rings[0]) == 5:
            cl = quad_centerline(rings[0])
            if cl:
                p, q, w = cl
                if w < cfg.get("min_width", 0):
                    continue
                ln = math.hypot(p[0] - q[0], p[1] - q[1])
                if any(inside(bb, sb) for sb in cfg.get("smart", [])) and ln < 60:
                    continue
                killed = False
                for kx0, ky0, kx1, ky1 in cfg.get("kill_segs", []):
                    if (math.hypot(p[0] - kx0, p[1] - ky0) < 8 and math.hypot(q[0] - kx1, q[1] - ky1) < 8) or (
                        math.hypot(p[0] - kx1, p[1] - ky1) < 8 and math.hypot(q[0] - kx0, q[1] - ky0) < 8
                    ):
                        killed = True
                        break
                for lx0, ly0, lx1, ly1 in cfg.get("kill_lines", []):
                    if killed:
                        break
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
                        killed = True
                        break
                if killed:
                    continue
                if ln >= min_seg:
                    segs.append((p, q))
                continue
        if any(inside(bb, sb) for sb in cfg.get("smart", [])):
            w_ = bb[2] - bb[0]
            h_ = bb[3] - bb[1]
            md = max(w_, h_)
            roundish = abs(w_ - h_) <= 3 and len(rings[0]) >= 12 and md <= 22
            if md < 250 and not roundish:
                continue
        if cfg.get("drop_glyphs"):
            h = bb[3] - bb[1]
            wdt = bb[2] - bb[0]
            if 18 < max(h, wdt) < 250 and h < 75:
                continue
        fills.append(rings)
    for _, cx, cy, r in plot.circles:
        pass  # none in these sheets

    x0, y0, x1, y1 = crop
    w, h = x1 - x0, y1 - y0
    pad = 40

    def fx(v):
        return round(v - x0 + pad, 1)

    def fy(v):
        return round(v - y0 + pad, 1)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w + 2 * pad:.0f} {h + 2 * pad:.0f}">',
        f'<g fill="none" stroke="currentColor" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round">',
    ]
    d = []
    for p, q in segs:
        d.append(f"M{fx(p[0])} {fy(p[1])}L{fx(q[0])} {fy(q[1])}")
    parts.append(f'<path d="{"".join(d)}"/>')
    parts.append('</g><g fill="currentColor" stroke="none" fill-rule="evenodd">')
    fd = []
    for rings in fills:
        for r in rings:
            fd.append(
                f"M{fx(r[0][0])} {fy(r[0][1])}"
                + "".join(f"L{fx(x)} {fy(y)}" for x, y in r[1:])
                + "Z"
            )
    parts.append(f'<path d="{"".join(fd)}"/>')
    parts.append("</g></svg>")
    with open(out_path, "w") as f:
        f.write("\n".join(parts))
    print(f"{view}: {len(segs)} strokes, {len(fills)} fills -> {out_path}")


if __name__ == "__main__":
    view, out = sys.argv[1], sys.argv[2]
    convert(view, out)
