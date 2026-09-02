"""Build logo SVGs from Pierre's hand-trimmed drawings.

Input: docs/design/aisc-logo/hand-editted-e2.svg / hand-editted-iso.svg
(Inkscape files, one fill group of thin filled quads, original plot coords).
They are read only, never written.

Outputs per view:
- hand-logo-<v>.svg          faithful: every quad collapsed to a centerline
                             stroke, hardware drawn with a fine stroke. This
                             is the full logo, it keeps all the detail.
- hand-logo-<v>-favicon.svg  for small sizes: collinear fragments joined,
  and -favicon-filled.svg    close parallel pairs merged, small hardware
                             dropped, and every bolt replaced by one simple
                             mark (a circle when the symbol is about round,
                             a rectangle when it is long), outline or
                             filled.

Bolts are found by ink density: a bolt is a lot of short strokes packed in
a small area, so the short segments are clustered by midpoint proximity and
the clusters that are small, thick and dense are bolts. This also catches
bolts that touch a plate line, which connected components cannot separate.
The detection is only used to simplify the favicon (a bolt becomes a dot),
the faithful output draws every stroke as it is in the drawing.

NOTE: the shipping artwork is NOT what this writes any more. Pierre cleaned
the tool output by hand (the detail callout balloons and the zigzag break
lines are gone) and ran it through an SVG optimizer, giving
hand-logo-e2-cleaned-optimized.svg and hand-logo-e2-favicon-cleaned.svg.
Rerunning this script does not reproduce those, and does not overwrite them
either (different names). Use it only to redo the pipeline from scratch.

Run from anywhere:
  python3 tools/hand2logo.py [e2] [iso]
"""
import math
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)

VIEWS = {
    "e2": "hand-editted-e2.svg",
    "iso": "hand-editted-iso.svg",
}

STROKE = 5.0          # base line width, the plotter pen quads are 5 units wide
BOLT_STROKE = 2.0     # fine stroke for bolts, nuts and the other small hardware
HEAVY_STROKE = 8.0    # width of a merged pair of close parallel lines
DOT_MIN_R = 5.0       # a favicon bolt mark is never smaller than this
DOT_RECT_ASPECT = 1.5  # longer than this and the bolt mark is a rectangle

FINE_MAX = 42.0       # an ink blob smaller than this is hardware, not structure
FINE_MIN_SEGS = 3     # a lone short segment is a dash, not hardware

SHORT_LEN = 28.0      # a bolt stroke is short, structure lines are long
CLUSTER_EPS = 9.0     # short strokes closer than this belong together
RESPLIT_EPS = 5.0     # tighter radius to break up an oversized cluster
BOLT_MIN_SEGS = 6     # a bolt symbol is drawn with many short strokes
BOLT_MIN_SIZE = 10.0  # smaller than this is a dash or a tick
BOLT_MAX_SIZE = 110.0  # a full 3d bolt (head + shank + nut) in the iso
BOLT_MIN_THIN = 6.0   # a bolt is a blob, not a sliver
BOLT_MIN_INK = 60.0   # total stroke length inside the blob
BOLT_MIN_DENS = 0.05  # ink per bbox area, a bolt is dense, a corner is not
ENGULF_LEN = 40.0     # a segment this short fully inside a bolt box is bolt

MAX_GAP = 14.0        # merge parallel lines up to this far apart (centre to centre)
MIN_PAR_LEN = 50.0    # only merge parallel lines at least this long
PAR_TOL = math.radians(2.5)
DP_EPS = 1.2          # collinear merge tolerance
JOIN_TOL = 1.0        # endpoint healing radius (plot coords are integers)

TOK = re.compile(r"([MmHhVvLlZz])|(-?\d+(?:\.\d+)?(?:e-?\d+)?)")


# ---------------------------------------------------------------- parsing

def parse_d(d):
    toks = [(a if a else float(b)) for a, b in TOK.findall(d)]
    rings, cur = [], []
    x = y = sx = sy = 0.0
    i, cmd = 0, None
    while i < len(toks):
        t = toks[i]
        if isinstance(t, str):
            cmd = t
            i += 1
            if cmd in "Zz":
                if cur:
                    rings.append(cur)
                    x, y = sx, sy
                    cur = []
                continue
        if cmd in "mM":
            if cmd == "m":
                x += toks[i]; y += toks[i + 1]
            else:
                x = toks[i]; y = toks[i + 1]
            i += 2
            if cur:
                rings.append(cur)
            cur = [(x, y)]; sx, sy = x, y
            cmd = "l" if cmd == "m" else "L"
        elif cmd == "l":
            x += toks[i]; y += toks[i + 1]; i += 2; cur.append((x, y))
        elif cmd == "L":
            x = toks[i]; y = toks[i + 1]; i += 2; cur.append((x, y))
        elif cmd == "h":
            x += toks[i]; i += 1; cur.append((x, y))
        elif cmd == "H":
            x = toks[i]; i += 1; cur.append((x, y))
        elif cmd == "v":
            y += toks[i]; i += 1; cur.append((x, y))
        elif cmd == "V":
            y = toks[i]; i += 1; cur.append((x, y))
        else:
            raise ValueError("unsupported path command %r" % cmd)
    if cur:
        rings.append(cur)
    return rings


def parse_svg(path):
    text = open(path).read()
    vb = [float(v) for v in re.search(r'viewBox="([\d\.\- ]+)"', text).group(1).split()]
    m = re.search(r'transform="translate\((-?[\d\.]+),(-?[\d\.]+)\)"', text)
    tx, ty = (float(m.group(1)), float(m.group(2))) if m else (0.0, 0.0)
    rings = []
    for d in re.findall(r'\bd="([^"]+)"', text):
        rings.extend(parse_d(d))
    return vb, (tx, ty), rings


# ---------------------------------------------------------------- geometry

def dist(p, q):
    return math.hypot(p[0] - q[0], p[1] - q[1])


def bbox(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def quad_centerline(pts):
    a, b, c, d = pts[0], pts[1], pts[2], pts[3]

    def mid(p, q):
        return ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)

    e = [dist(a, b), dist(b, c), dist(c, d), dist(d, a)]
    if min(e[0], e[2]) > 0 and max(e[1], e[3]) <= min(e[0], e[2]) * 0.55:
        return mid(d, a), mid(b, c)
    if min(e[1], e[3]) > 0 and max(e[0], e[2]) <= min(e[1], e[3]) * 0.55:
        return mid(a, b), mid(c, d)
    return None


def split_rings(rings):
    """-> (segments [(p, q)], fills [ring])"""
    segs, fills = [], []
    for r in rings:
        if len(r) < 3:
            continue  # zero-area leftovers
        if len(r) == 5 and dist(r[0], r[4]) < 0.01:
            r = r[:4]
        if len(r) == 4:
            cl = quad_centerline(r)
            if cl:
                segs.append(cl)
            else:
                fills.append(r)
        else:
            fills.append(r)
    return segs, fills


# ------------------------------------------------------- graph reconstruction

def heal_endpoints(segs, tol=JOIN_TOL):
    """Snap endpoints within tol onto a shared point, drop duplicates."""
    pts = []
    for p, q in segs:
        pts.append(list(p))
        pts.append(list(q))
    parent = list(range(len(pts)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    cell = int(math.ceil(tol))
    grid = defaultdict(list)
    for i, p in enumerate(pts):
        grid[(int(p[0] // cell), int(p[1] // cell))].append(i)
    for (cx, cy), idxs in list(grid.items()):
        near = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                near.extend(grid.get((cx + dx, cy + dy), []))
        for i in idxs:
            for j in near:
                if j > i and dist(pts[i], pts[j]) <= tol:
                    parent[find(i)] = find(j)
    groups = defaultdict(list)
    for i in range(len(pts)):
        groups[find(i)].append(i)
    rep = {}
    for members in groups.values():
        ax = sum(pts[i][0] for i in members) / len(members)
        ay = sum(pts[i][1] for i in members) / len(members)
        for i in members:
            rep[i] = (ax, ay)
    healed, seen = [], set()
    for k in range(len(segs)):
        p, q = rep[2 * k], rep[2 * k + 1]
        if dist(p, q) <= 0.01:
            continue
        key = tuple(sorted(((round(p[0], 1), round(p[1], 1)),
                            (round(q[0], 1), round(q[1], 1)))))
        if key in seen:
            continue  # overdrawn duplicate stroke
        seen.add(key)
        healed.append((key[0], key[1]))
    return healed


def components(segs):
    """Group segments that touch into connected components."""
    node = {}
    parent = list(range(len(segs)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, (p, q) in enumerate(segs):
        for pt in (p, q):
            key = (round(pt[0], 1), round(pt[1], 1))
            if key in node:
                parent[find(i)] = find(node[key])
            else:
                node[key] = i
    groups = defaultdict(list)
    for i in range(len(segs)):
        groups[find(i)].append(i)
    return list(groups.values())


def build_chains(segs):
    """Walk the segment graph into open chains and closed cycles."""
    node_segs = defaultdict(list)
    for i, (p, q) in enumerate(segs):
        node_segs[p].append(i)
        node_segs[q].append(i)
    used = [False] * len(segs)
    chains = []

    def walk(start_node, seg_i):
        used[seg_i] = True
        p, q = segs[seg_i]
        nxt = q if p == start_node else p
        pts = [start_node, nxt]
        while True:
            cand = [j for j in node_segs[nxt] if not used[j]]
            if len(node_segs[nxt]) != 2 or not cand:
                break
            j = cand[0]
            used[j] = True
            p, q = segs[j]
            nxt = q if p == nxt else p
            pts.append(nxt)
        return pts

    for node, lst in node_segs.items():
        if len(lst) != 2:
            for i in lst:
                if not used[i]:
                    chains.append(walk(node, i))
    for i in range(len(segs)):
        if not used[i]:
            p, _ = segs[i]
            chains.append(walk(p, i))
    return chains


# ------------------------------------------------------------- bolt finding

def blob_features(segs, members):
    pts = [p for i in members for p in segs[i]]
    x0, y0, x1, y1 = bbox(pts)
    ink = sum(dist(*segs[i]) for i in members)
    return (len(members), x1 - x0, y1 - y0, ink, (x0, y0, x1, y1))


def same_shape(a, b):
    """Same symbol, allowing for the plotter's sub-unit jitter."""
    return (abs(a[0] - b[0]) <= 1
            and abs(a[1] - b[1]) <= 2.5 and abs(a[2] - b[2]) <= 2.5
            and abs(a[3] - b[3]) <= 0.05 * max(a[3], b[3]))


def boxes_touch(a, b, pad):
    return not (a[2] < b[0] - pad or a[0] > b[2] + pad
                or a[3] < b[1] - pad or a[1] > b[3] + pad)


def cluster_short(segs, idx=None, eps=CLUSTER_EPS):
    """Cluster the midpoints of the short segments by proximity.

    This is the density idea: a bolt is a lot of short strokes packed in a
    small area, and it works even when the bolt touches a plate line, which
    breaks connected components (the plate line is long, so it never enters
    a cluster)."""
    top = idx is None
    if top:
        idx = [i for i, (p, q) in enumerate(segs) if dist(p, q) <= SHORT_LEN]
    mids = {}
    grid = defaultdict(list)
    for i in idx:
        (px, py), (qx, qy) = segs[i]
        m = ((px + qx) / 2, (py + qy) / 2)
        mids[i] = m
        grid[(int(m[0] // eps), int(m[1] // eps))].append(i)
    parent = {i: i for i in idx}

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    e2 = eps * eps
    for (cx, cy), lst in grid.items():
        for dx, dy in ((0, 0), (1, -1), (1, 0), (1, 1), (0, 1)):
            other = grid.get((cx + dx, cy + dy))
            if not other:
                continue
            for i in lst:
                xi, yi = mids[i]
                for j in other:
                    if (dx, dy) == (0, 0) and j <= i:
                        continue
                    xj, yj = mids[j]
                    if (xi - xj) ** 2 + (yi - yj) ** 2 <= e2:
                        parent[find(i)] = find(j)
    groups = defaultdict(list)
    for i in idx:
        groups[find(i)].append(i)
    out = []
    for g in groups.values():
        f = blob_features(segs, g)
        # a chain of dashes next to a bolt can weld everything into one
        # oversized cluster: re-split it with a tighter radius, the bolt
        # strokes stay together, the dash chain falls apart. The parts are
        # tagged: a piece of an oversized cluster can also be a piece of a
        # zigzag arc, so it only becomes a bolt if it is shaped like one.
        if (top and max(f[1], f[2]) > BOLT_MAX_SIZE
                and eps > RESPLIT_EPS):
            out.extend((m, True)
                       for m, _ in cluster_short(segs, g, RESPLIT_EPS))
        else:
            out.append((g, eps <= RESPLIT_EPS))
    return out


def find_bolts(segs, marked=None):
    """-> list of families, each a list of (members, features).
    marked: optional list of segment index groups from a hand marked file,
    accepted as bolts no matter what the filters say.

    A bolt is a dense blob of short strokes in a small area (Pierre's idea).
    The short strokes are clustered by midpoint proximity, a bolt often
    splits into head, shank and nut clusters, so clusters whose boxes nearly
    touch are merged while the result stays bolt sized. Blobs that are big
    enough, small enough and dense enough are bolts, dashes and stray ticks
    fail the ink and thinness tests. Leftover fragments next to an accepted
    bolt are attached to it, and any short segment fully inside a bolt box
    joins too (the shank sides, for one). Identical bolts are then grouped
    into families so they can share one <defs> glyph."""
    clusters = cluster_short(segs)
    pieces = []
    small_bits = []
    for m, resplit in clusters:
        f = blob_features(segs, m)
        if f[0] >= 2 and f[3] >= 15:
            pieces.append([list(m), f, resplit])
        else:
            small_bits.append((m, f, resplit))
    changed = True
    while changed:
        changed = False
        for i in range(len(pieces)):
            if not pieces[i]:
                continue
            for j in range(i + 1, len(pieces)):
                if not pieces[j]:
                    continue
                a, b = pieces[i][1][4], pieces[j][1][4]
                if not boxes_touch(a, b, 6.5):
                    continue
                x0, y0 = min(a[0], b[0]), min(a[1], b[1])
                x1, y1 = max(a[2], b[2]), max(a[3], b[3])
                if max(x1 - x0, y1 - y0) > BOLT_MAX_SIZE:
                    continue
                pieces[i][0].extend(pieces[j][0])
                pieces[i][1] = blob_features(segs, pieces[i][0])
                pieces[i][2] = pieces[i][2] and pieces[j][2]
                pieces[j] = None
                changed = True
    pieces = [p for p in pieces if p]

    # the tighter re-split radius also knocks single strokes off a bolt (a
    # hexagon face sits alone at that radius): give them back to the
    # re-split piece they sit on, so its shape can match an intact twin
    for p in pieces:
        if not p[2]:
            continue
        x0, y0, x1, y1 = p[1][4]
        for k, (m, f, resplit) in enumerate(small_bits):
            if m is None:
                continue
            bx0, by0, bx1, by1 = f[4]
            if (x0 - 8 <= bx0 and bx1 <= x1 + 8
                    and y0 - 8 <= by0 and by1 <= y1 + 8):
                p[0].extend(m)
                small_bits[k] = (None, f, resplit)
        p[1] = blob_features(segs, p[0])
    small_bits = [b for b in small_bits if b[0] is not None]

    # direct acceptance is only for normal clusters: a piece of a re-split
    # oversized cluster can be a dense patch of a zigzag arc, those only get
    # in through the rescue below, by looking like an accepted bolt
    bolts, rejected = [], []
    for m, f, resplit in pieces:
        nseg, w, h, ink, bb = f
        big, small = max(w, h), min(w, h)
        dens = ink / max(1.0, w * h)
        if (not resplit and nseg >= BOLT_MIN_SEGS
                and BOLT_MIN_SIZE <= big <= BOLT_MAX_SIZE
                and small >= BOLT_MIN_THIN and ink >= BOLT_MIN_INK
                and dens >= BOLT_MIN_DENS):
            bolts.append([m, f])
        else:
            rejected.append((m, f, resplit))

    # rescue: a rejected blob shaped like an accepted bolt IS a bolt, this
    # keeps two identical bolts from ending up one red one black
    accepted = [b[1] for b in bolts]
    still = []
    for m, f, resplit in rejected:
        if any(abs(f[0] - a[0]) <= 3
               and abs(f[1] - a[1]) <= 4 and abs(f[2] - a[2]) <= 4
               and abs(f[3] - a[3]) <= 0.12 * max(f[3], a[3])
               for a in accepted):
            bolts.append([m, f])
        else:
            still.append((m, f, resplit))

    # attach the crumbs: rejected fragments sitting on an accepted bolt.
    # Re-split leftovers stay out (arc patches hug the bolt that welded
    # them into the oversized cluster), and their segments are also kept
    # away from the engulf pass below.
    forbidden = set()
    for m, f, resplit in small_bits + still:
        if resplit:
            forbidden.update(m)
            continue
        for b in bolts:
            if boxes_touch(f[4], b[1][4], 6.0):
                b[0].extend(m)
                b[1] = blob_features(segs, b[0])
                break

    # hand marks beat every filter: a marked group is a bolt, full stop
    if marked:
        for m in marked:
            forbidden.difference_update(m)
            taken_here = set(i for b in bolts for i in b[0])
            m = [i for i in m if i not in taken_here]
            if not m:
                continue
            f = blob_features(segs, m)
            for b in bolts:
                if boxes_touch(f[4], b[1][4], 4.0):
                    b[0].extend(m)
                    b[1] = blob_features(segs, b[0])
                    break
            else:
                bolts.append([m, f])

    # engulf: mid length segments next to a bolt box (a nut face is longer
    # than the short stroke cut) so a bolt is never half coloured; iterate,
    # the box grows around the nut, but never past bolt size
    taken = set(i for b in bolts for i in b[0])
    changed = True
    while changed:
        changed = False
        for i, (p, q) in enumerate(segs):
            if i in taken or i in forbidden or dist(p, q) > ENGULF_LEN:
                continue
            for b in bolts:
                x0, y0, x1, y1 = b[1][4]
                if not (x0 - 10 <= p[0] <= x1 + 10
                        and y0 - 10 <= p[1] <= y1 + 10
                        and x0 - 10 <= q[0] <= x1 + 10
                        and y0 - 10 <= q[1] <= y1 + 10):
                    continue
                f2 = blob_features(segs, b[0] + [i])
                if max(f2[1], f2[2]) > BOLT_MAX_SIZE:
                    continue
                b[0].append(i)
                b[1] = f2
                taken.add(i)
                changed = True
                break

    groups = []
    for m, f in bolts:
        for g in groups:
            if same_shape(f, g[0]):
                g[1].append((m, f))
                break
        else:
            groups.append((f, [(m, f)]))
    return [g[1] for g in groups]


# ------------------------------------------------------------ simplification

def dp(points, eps):
    """Douglas-Peucker."""
    if len(points) < 3:
        return points

    def d_perp(p, a, b):
        ax, ay = a; bx, by = b; px, py = p
        dx, dy = bx - ax, by - ay
        ln = math.hypot(dx, dy)
        if ln < 1e-9:
            return dist(p, a)
        return abs((px - ax) * dy - (py - ay) * dx) / ln

    dmax, idx = 0.0, 0
    for i in range(1, len(points) - 1):
        dd = d_perp(points[i], points[0], points[-1])
        if dd > dmax:
            dmax, idx = dd, i
    if dmax > eps:
        return dp(points[: idx + 1], eps)[:-1] + dp(points[idx:], eps)
    return [points[0], points[-1]]


def seg_angle(p, q):
    return math.atan2(q[1] - p[1], q[0] - p[0]) % math.pi  # undirected


def coalesce_collinear(lines):
    """Merge segments on the same line that touch or overlap.

    Chains get chopped at every junction, so a beam flange arrives as a dozen
    fragments; this puts them back together into one line."""
    buckets = defaultdict(list)

    def line_of(k):
        p, q = lines[k]
        ln = dist(p, q)
        ux, uy = (q[0] - p[0]) / ln, (q[1] - p[1]) / ln
        if ux < 0 or (ux == 0 and uy < 0):
            ux, uy = -ux, -uy
        return ux, uy, -uy * p[0] + ux * p[1]

    for k, (p, q) in enumerate(lines):
        if dist(p, q) < 0.01:
            continue
        deg = seg_angle(p, q) * 180 / math.pi
        _, _, off = line_of(k)
        for db in (0, 1):
            for do in (0, 1):
                buckets[(int(deg // 1) + db, int(off // 3) + do)].append(k)
    parent = list(range(len(lines)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def off_line(pt, a):
        pa, qa = lines[a]
        ln = dist(pa, qa)
        ux, uy = (qa[0] - pa[0]) / ln, (qa[1] - pa[1]) / ln
        return abs(-uy * (pt[0] - pa[0]) + ux * (pt[1] - pa[1]))

    for idxs in buckets.values():
        for a in idxs:
            uxa, uya, _ = line_of(a)
            pa, qa = lines[a]
            ta = sorted((0.0, (qa[0] - pa[0]) * uxa + (qa[1] - pa[1]) * uya))
            for b in idxs:
                if b <= a or find(a) == find(b):
                    continue
                uxb, uyb, _ = line_of(b)
                if abs(uxa * uyb - uya * uxb) > 0.006:  # ~0.35 degree
                    continue
                pb, qb = lines[b]
                if off_line(pb, a) > 1.2 or off_line(qb, a) > 1.2:
                    continue
                tb = sorted(((pb[0] - pa[0]) * uxa + (pb[1] - pa[1]) * uya,
                             (qb[0] - pa[0]) * uxa + (qb[1] - pa[1]) * uya))
                if tb[0] > ta[1] + 2 or ta[0] > tb[1] + 2:
                    continue  # a real gap, dashes stay dashes
                parent[find(a)] = find(b)
    groups = defaultdict(list)
    for k in range(len(lines)):
        if dist(*lines[k]) >= 0.01:
            groups[find(k)].append(k)
    out = []
    for members in groups.values():
        if len(members) == 1:
            out.append(lines[members[0]])
            continue
        ref = max(members, key=lambda k: dist(*lines[k]))
        pr, qr = lines[ref]
        ln = dist(pr, qr)
        ux, uy = (qr[0] - pr[0]) / ln, (qr[1] - pr[1]) / ln
        ts = [(pt[0] - pr[0]) * ux + (pt[1] - pr[1]) * uy
              for k in members for pt in lines[k]]
        lo, hi = min(ts), max(ts)
        out.append(((pr[0] + ux * lo, pr[1] + uy * lo),
                    (pr[0] + ux * hi, pr[1] + uy * hi)))
    return out


def merge_parallel(lines, max_gap=MAX_GAP):
    """Replace a pair of close parallel lines by one line on their midline."""
    items = []
    for p, q in lines:
        ln = dist(p, q)
        if ln < 0.01:
            continue
        items.append({"p": p, "q": q, "len": ln, "ang": seg_angle(p, q)})
    used = [False] * len(items)
    grid = defaultdict(list)
    cell = 64
    for i, it in enumerate(items):
        x0, y0, x1, y1 = bbox([it["p"], it["q"]])
        for cx in range(int(x0 // cell), int(x1 // cell) + 1):
            for cy in range(int(y0 // cell), int(y1 // cell) + 1):
                grid[(cx, cy)].append(i)
    thin, heavy = [], []
    for i, a in enumerate(items):
        if used[i] or a["len"] < MIN_PAR_LEN:
            continue
        cand = set()
        x0, y0, x1, y1 = bbox([a["p"], a["q"]])
        for cx in range(int(x0 // cell) - 1, int(x1 // cell) + 2):
            for cy in range(int(y0 // cell) - 1, int(y1 // cell) + 2):
                cand.update(grid.get((cx, cy), []))
        ux = (a["q"][0] - a["p"][0]) / a["len"]
        uy = (a["q"][1] - a["p"][1]) / a["len"]
        best = None
        for j in cand:
            if j == i or used[j]:
                continue
            b = items[j]
            if b["len"] < MIN_PAR_LEN:
                continue
            d_ang = abs(a["ang"] - b["ang"])
            if min(d_ang, math.pi - d_ang) > PAR_TOL:
                continue
            gap = abs(mid_off(a, b, ux, uy))
            if gap < 1.0 or gap > max_gap:
                continue
            tb = sorted(((b["p"][0] - a["p"][0]) * ux + (b["p"][1] - a["p"][1]) * uy,
                         (b["q"][0] - a["p"][0]) * ux + (b["q"][1] - a["p"][1]) * uy))
            ov = min(a["len"], tb[1]) - max(0.0, tb[0])
            if ov < 0.6 * min(a["len"], b["len"]):
                continue
            if min(a["len"], b["len"]) < 0.5 * max(a["len"], b["len"]):
                continue
            if best is None or gap < best[1]:
                best = (j, gap, tb)
        if best is None:
            continue
        j, gap, tb = best
        b = items[j]
        used[i] = used[j] = True
        lo, hi = min(0.0, tb[0]), max(a["len"], tb[1])
        half = mid_off(a, b, ux, uy) / 2
        heavy.append(((a["p"][0] + ux * lo - uy * half,
                       a["p"][1] + uy * lo + ux * half),
                      (a["p"][0] + ux * hi - uy * half,
                       a["p"][1] + uy * hi + ux * half)))
    for i, it in enumerate(items):
        if not used[i]:
            thin.append((it["p"], it["q"]))
    return thin, heavy


def mid_off(a, b, ux, uy):
    """Signed perpendicular offset of b's midpoint from line a."""
    mbx = (b["p"][0] + b["q"][0]) / 2 - a["p"][0]
    mby = (b["p"][1] + b["q"][1]) / 2 - a["p"][1]
    return -uy * mbx + ux * mby


# ---------------------------------------------------------------- output

def fx(v):
    s = "%.1f" % v
    return s[:-2] if s.endswith(".0") else s


def path_line(pts):
    d = "M%s %s" % (fx(pts[0][0]), fx(pts[0][1]))
    for p in pts[1:]:
        d += "L%s %s" % (fx(p[0]), fx(p[1]))
    return d


def write_svg(path, vb, body, stroke=STROKE):
    x0, y0, w, h = vb
    out = ['<svg xmlns="http://www.w3.org/2000/svg" '
           'viewBox="%s %s %s %s">' % (fx(x0), fx(y0), fx(w), fx(h))]
    out.append('<g fill="none" stroke="currentColor" stroke-width="%s" '
               'stroke-linecap="round" stroke-linejoin="round">' % fx(stroke))
    out.extend(body)
    out.append("</g></svg>")
    open(path, "w").write("\n".join(out) + "\n")


MARK_STROKE = re.compile(
    r'stroke\s*[:=]\s*"?\'?(#[0-9a-fA-F]{3,6}|red|blue|green|magenta)')


def read_marks(view, segs):
    """Read hand-marks-<view>.svg, a copy of the faithful output where the
    bolts the detector missed were coloured by hand (any stroke colour that
    is not black). Returns groups of healed segment indices, or None.

    Marked strokes are matched back to the healed segments by midpoint and
    length, so recolouring in Inkscape is enough, nothing else may move."""
    path = os.path.join(BASE, "hand-marks-%s.svg" % view)
    if not os.path.exists(path):
        return None
    text = open(path).read()
    grid = defaultdict(list)
    for i, (p, q) in enumerate(segs):
        m = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
        grid[(int(m[0] // 4), int(m[1] // 4))].append((i, m, dist(p, q)))
    hits = []
    for el in re.findall(r"<path[^>]*>", text):
        mcol = MARK_STROKE.search(el)
        if not mcol or mcol.group(1).lower() in ("#000", "#000000", "#212121"):
            continue
        md = re.search(r'\bd="([^"]+)"', el)
        if not md:
            continue
        for ring in parse_d(md.group(1)):
            for k in range(len(ring) - 1):
                p, q = ring[k], ring[k + 1]
                mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
                ln = dist(p, q)
                best = None
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        for i, m, l2 in grid.get(
                                (int(mx // 4) + dx, int(my // 4) + dy), ()):
                            d = dist((mx, my), m)
                            if (d <= 2 and abs(ln - l2) <= 2
                                    and (best is None or d < best[0])):
                                best = (d, i)
                if best:
                    hits.append(best[1])
    if not hits:
        return None
    groups = [m for m, _ in cluster_short(segs, sorted(set(hits)), 15.0)]
    print("  %d hand marked strokes -> %d marked bolts"
          % (len(hits), len(groups)))
    return groups


def main(view):
    src = os.path.join(BASE, VIEWS[view])
    vb, (tx, ty), rings = parse_svg(src)
    vb_out = (-tx, -ty, vb[2], vb[3])
    segs, fills = split_rings(rings)
    healed = heal_endpoints(segs)
    families = find_bolts(healed, read_marks(view, healed))
    bolt_segs = set()
    for fam in families:
        for members, _ in fam:
            bolt_segs.update(members)
    print("%s: %d segments, %d fills, %d bolt shapes in %d families"
          % (view, len(segs), len(fills),
             sum(len(f) for f in families), len(families)))

    # small hardware that is not one of the repeated bolts still gets the
    # fine stroke, so nuts and washers do not turn into black lumps
    fine = FineIndex(fine_boxes(healed, bolt_segs))

    # ---- faithful
    body, fine_els = [], []
    for i, (p, q) in enumerate(healed):
        el = '<path d="%s"/>' % path_line([p, q])
        if i in bolt_segs or fine.covers((p, q)):
            fine_els.append(el)
        else:
            body.append(el)
    if fine_els:
        body.append('<g stroke-width="%s">' % fx(BOLT_STROKE))
        body.extend(fine_els)
        body.append("</g>")
    for f in fills:
        body.append('<path fill="currentColor" stroke="none" d="%sZ"/>'
                    % path_line(f))
    out = os.path.join(BASE, "hand-logo-%s.svg" % view)
    write_svg(out, vb_out, body)
    print("  faithful -> %s (%d lines, %d fine)"
          % (os.path.basename(out), len(healed), len(fine_els)))

    # ---- favicon: simplified lines, small hardware dropped, bolts as dots
    lines = []
    for ch in build_chains([s for i, s in enumerate(healed)
                            if i not in bolt_segs]):
        pts = dp(ch, DP_EPS) if len(ch) > 2 else ch
        for k in range(len(pts) - 1):
            seg = (pts[k], pts[k + 1])
            # the fine hardware (weld marks, small clips) is invisible at
            # favicon size, it only muddies the drawing: drop it
            if not fine.covers(seg):
                lines.append(seg)
    thin, heavy = merge_parallel(coalesce_collinear(lines))

    body = []
    for p, q in thin:
        body.append('<path d="%s"/>' % path_line([p, q]))
    for p, q in heavy:
        body.append('<path stroke-width="%s" d="%s"/>'
                    % (fx(HEAVY_STROKE), path_line([p, q])))
    for f in fills:
        x0, y0, x1, y1 = bbox(f)
        c = ((x0 + x1) / 2, (y0 + y1) / 2)
        if not in_any_bolt(c, families):
            body.append('<path fill="currentColor" stroke="none" d="%sZ"/>'
                        % path_line(f))

    # every bolt becomes one simple mark, sized from the symbol itself: a
    # circle when the symbol is about round (a face on head), a rectangle
    # when it is long (a side view bolt through a plate)
    marks = []
    for fam in families:
        for _, f in fam:
            x0, y0, x1, y1 = f[4]
            w, h = x1 - x0, y1 - y0
            if max(w, h) > DOT_RECT_ASPECT * min(w, h):
                marks.append('<rect x="%s" y="%s" width="%s" height="%s"/>'
                             % (fx(x0), fx(y0), fx(w), fx(h)))
            else:
                r = max(DOT_MIN_R, min(w, h) / 2)
                marks.append('<circle cx="%s" cy="%s" r="%s"/>'
                             % (fx((x0 + x1) / 2), fx((y0 + y1) / 2), fx(r)))

    for tag, style in (("favicon", 'fill="none"'),
                       ("favicon-filled", 'fill="currentColor" stroke="none"')):
        out = os.path.join(BASE, "hand-logo-%s-%s.svg" % (view, tag))
        write_svg(out, vb_out,
                  body + ['<g id="bolts" %s>' % style] + marks + ["</g>"])
        print("  %s -> %s: %d lines, %d heavy, %d bolt marks"
              % (tag, os.path.basename(out), len(thin), len(heavy),
                 len(marks)))


def in_any_bolt(pt, families):
    for fam in families:
        for _, f in fam:
            x0, y0, x1, y1 = f[4]
            if x0 - 8 <= pt[0] <= x1 + 8 and y0 - 8 <= pt[1] <= y1 + 8:
                return True
    return False


def fine_boxes(segs, skip):
    """Boxes of the small ink blobs that are not already known bolts."""
    boxes = []
    for members in components(segs):
        if len(members) < FINE_MIN_SEGS or members[0] in skip:
            continue
        pts = [p for i in members for p in segs[i]]
        x0, y0, x1, y1 = bbox(pts)
        if max(x1 - x0, y1 - y0) <= FINE_MAX and min(x1 - x0, y1 - y0) >= 4:
            boxes.append((x0 - 1, y0 - 1, x1 + 1, y1 + 1))
    return boxes


class FineIndex(object):
    """Point-in-any-fine-box test, on a grid."""

    CELL = 64

    def __init__(self, boxes):
        self.boxes = boxes
        self.grid = defaultdict(list)
        for k, (x0, y0, x1, y1) in enumerate(boxes):
            for cx in range(int(x0 // self.CELL), int(x1 // self.CELL) + 1):
                for cy in range(int(y0 // self.CELL), int(y1 // self.CELL) + 1):
                    self.grid[(cx, cy)].append(k)

    def covers(self, pts):
        p = pts[0]
        for k in self.grid.get((int(p[0] // self.CELL), int(p[1] // self.CELL)), []):
            x0, y0, x1, y1 = self.boxes[k]
            if all(x0 <= q[0] <= x1 and y0 <= q[1] <= y1 for q in pts):
                return True
        return False


if __name__ == "__main__":
    # dlignos picked the 2D view in #263, so e2 is the default; the iso
    # input is still there, pass "iso" to rebuild it
    for v in (sys.argv[1:] or ["e2"]):
        main(v)
