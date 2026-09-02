"""Render the sculpture from reference/sculpture.yaml as a line drawing.

  python3 tools/sculpture_render.py reference/sculpture.yaml out.svg
        [--view iso|west|east|north|south|plan|AZ,EL] [--scale 4]
        [--no-bolts] [--drop 12C1,12D1] [--web-only 5B2,5B1]
        [--scale-z 3] [--scale-plan 2] [--seg 6]

Pipeline, in order:

1. load: read the YAML, apply the edits (drop members, scale an axis,
   strip flanges), resolve level names in coordinates.
2. solids: every member becomes its real cross section (I, C, T, HSS,
   pipe, rod, double angle, joist) extruded along its axis line. Sections
   come from the SECTIONS table, AISC manual values.
3. camera: an orthographic view. Named views or any azimuth and
   elevation in degrees (azimuth = compass bearing of the camera).
4. hidden lines: the painter's trick. Every face is filled white and
   drawn back to front, back faces are culled, long members are cut
   into short segments so the depth sort stays honest. No real hidden
   line removal, no dashed hidden edges.
5. style: black edges, white faces, bolts as black dots on the face
   nearest the camera. One <g> per member, named by its mark.
"""
import math
import re
import sys

import yaml

# ------------------------------------------------------------- sections
# kind, then the dims in inches. I and C: d, bf, tw, tf. T: d, bf, tw, tf
# (d is the tee depth). RHS: h, b, t. O: outer diameter, wall (0 = solid).
# 2L: leg along the gusset, outstanding leg, t. K: depth (open web joist).
SECTIONS = {
    "W12x96": ("I", 12.7, 12.2, 0.550, 0.900),
    "W12x53": ("I", 12.1, 10.0, 0.345, 0.575),
    "W10x33": ("I", 9.73, 7.96, 0.290, 0.435),
    "W16x36": ("I", 15.9, 6.99, 0.295, 0.430),
    "W16x31": ("I", 15.9, 5.53, 0.275, 0.440),
    "W16x26": ("I", 15.7, 5.50, 0.250, 0.345),
    "W14x26": ("I", 13.9, 5.03, 0.255, 0.420),
    "W12x26": ("I", 12.2, 6.49, 0.230, 0.380),
    "W12x19": ("I", 12.2, 4.01, 0.235, 0.350),
    "W10x19": ("I", 10.2, 4.02, 0.250, 0.395),
    "W8x10": ("I", 7.89, 3.94, 0.170, 0.205),
    "W6x25": ("I", 6.38, 6.08, 0.320, 0.455),
    "C12x20.7": ("C", 12.0, 2.94, 0.282, 0.501),
    "C10x15.3": ("C", 10.0, 2.60, 0.240, 0.436),
    "C9x13.4": ("C", 9.0, 2.43, 0.233, 0.413),
    "C8x11.5": ("C", 8.0, 2.26, 0.220, 0.390),
    "HSS6x4x1/4": ("RHS", 6.0, 4.0, 0.233),
    "HSS4x4x1/4": ("RHS", 4.0, 4.0, 0.233),
    "PIPE 4 STD": ("O", 4.5, 0.237),
    "WT4x14": ("T", 4.03, 8.03, 0.285, 0.465),
    "WT4x12": ("T", 3.99, 8.02, 0.245, 0.400),
    "WT4x9": ("T", 4.07, 5.25, 0.230, 0.330),
    "2L3x2x1/4": ("2L", 3.0, 2.0, 0.25),
    "2L3x3x1/4": ("2L", 3.0, 3.0, 0.25),
    "RB3/4": ("O", 0.75, 0),
    "12K3": ("K", 12.0),
}

# member groups: which YAML lists hold members, and whether their line is
# the top of steel (profile hangs below) or the centre line
GROUPS = {"column": "centre", "girders": "tos", "beams": "tos", "posts": "centre",
          "braces": "centre", "joists": "tos"}


def section_key(s):
    return re.sub(r"\s*\(.*\)\s*$", "", str(s)).strip()


# ------------------------------------------------------------- profiles
# A profile is a list of polygons in local (a, b): a across the member,
# b along its depth, b positive = down for a horizontal member. Centred on
# the section, so a TOS member gets shifted by +d/2 afterwards.

def ccw(p):
    s = sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))
    return p if s > 0 else p[::-1]


def prof_I(d, bf, tw, tf):
    h, w, x, t = d / 2, bf / 2, tw / 2, tf
    return [ccw([(-w, -h), (w, -h), (w, -h + t), (x, -h + t), (x, h - t), (w, h - t),
                 (w, h), (-w, h), (-w, h - t), (-x, h - t), (-x, -h + t), (-w, -h + t)])]


def prof_C(d, bf, tw, tf):  # web at a = -bf/2, flanges to +a
    h, x = d / 2, -bf / 2
    return [ccw([(x, -h), (x + bf, -h), (x + bf, -h + tf), (x + tw, -h + tf),
                 (x + tw, h - tf), (x + bf, h - tf), (x + bf, h), (x, h)])]


def prof_T(d, bf, tw, tf):  # flange at the top (b = -d/2), stem down
    h, w, x = d / 2, bf / 2, tw / 2
    return [ccw([(-w, -h), (w, -h), (w, -h + tf), (x, -h + tf), (x, h), (-x, h), (-x, -h + tf), (-w, -h + tf)])]


def prof_2L(leg, out, t):  # two angles back to back, 3/8 gap, as one tee
    gap = 0.375
    return prof_T(leg, 2 * out + gap, 2 * t + gap, t)


def prof_rect(h, b):
    return [ccw([(-b / 2, -h / 2), (b / 2, -h / 2), (b / 2, h / 2), (-b / 2, h / 2)])]


def prof_O(dia, n=16):
    r = dia / 2
    return [ccw([(r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n)) for i in range(n)])]


def bolt_face(sec, side):
    """Where a bolt dot sits across the member (local a), on the side
    that looks at the camera: the web for I, C and T shapes, the wall
    for hollow sections, the chord for a joist."""
    kind, *dims = SECTIONS[sec]
    if kind in ("I", "T"):
        return side * dims[2] / 2
    if kind == "C":
        return -dims[1] / 2 + (dims[2] if side > 0 else 0)
    if kind == "2L":
        return side * (dims[2] + 0.19)
    if kind == "RHS":
        return side * dims[1] / 2
    if kind == "O":
        return side * dims[0] / 2
    return side * 2.0


def profile(sec, web_only=False):
    kind, *dims = SECTIONS[sec]
    if kind == "I":
        d, bf, tw, tf = dims
        return prof_rect(d, tw) if web_only else prof_I(*dims), d
    if kind == "C":
        d, bf, tw, tf = dims
        return prof_rect(d, tw) if web_only else prof_C(*dims), d
    if kind == "T":
        d = dims[0]
        return prof_rect(d, dims[2]) if web_only else prof_T(*dims), d
    if kind == "2L":
        return prof_2L(*dims), dims[0]
    if kind == "RHS":
        return prof_rect(dims[0], dims[1]), dims[0]
    if kind == "O":
        return prof_O(dims[0]), dims[0]
    raise ValueError(sec)


# ---------------------------------------------------------------- vectors
def sub(a, b): return [a[i] - b[i] for i in range(3)]
def add(a, b): return [a[i] + b[i] for i in range(3)]
def mul(a, k): return [a[i] * k for i in range(3)]
def dot(a, b): return sum(a[i] * b[i] for i in range(3))
def cross(a, b): return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
def norm(a):
    n = math.sqrt(dot(a, a))
    return [x / n for x in a] if n else a


def frame(p0, p1, facing=None, stem_up=False):
    """Local frame of a member: u along it, w along its depth, v = w x u.
    Right handed (v, w, u), so a CCW profile edge (P_i -> P_i+1) has the
    outward side face normal (P_i+1 - P_i) x u."""
    u = norm(sub(p1, p0))
    if facing is not None:
        w = norm(facing)
    elif abs(u[2]) > 0.99:  # vertical: depth along N, the column convention
        w = [0, 1, 0]
    else:  # depth straight down, projected perpendicular to the axis
        down = [0, 0, -1]
        w = norm(sub(down, mul(u, dot(down, u))))
    if stem_up:
        w = mul(w, -1)
    v = cross(w, u)
    return u, v, w


# ---------------------------------------------------------------- solids
# A solid is a list of faces. A face is (points3d, stroke_edges) where
# stroke_edges lists the index pairs of the polygon edges to draw.

def prism(p0, p1, polys, u, v, w, seg, shift=0.0):
    """Extrude the polygons from p0 to p1, cut into segments <= seg long.
    `shift` moves the profile along w (d/2 for top-of-steel members)."""
    L = math.sqrt(dot(sub(p1, p0), sub(p1, p0)))
    n = max(1, int(math.ceil(L / seg)))
    faces = []
    for poly in polys:
        base = [add(p0, add(mul(v, a), mul(w, b + shift))) for a, b in poly]
        m = len(base)
        for k in range(n):
            A = [add(pt, mul(u, L * k / n)) for pt in base]
            B = [add(pt, mul(u, L * (k + 1) / n)) for pt in base]
            for i in range(m):
                j = (i + 1) % m
                # side quad: the two longitudinal edges, plus the end edge
                # at a member end, so the end is drawn even when the cap
                # faces away from the camera
                edges = [(1, 2), (3, 0)]
                if k == 0:
                    edges.append((0, 1))
                if k == n - 1:
                    edges.append((2, 3))
                faces.append(([A[i], A[j], B[j], B[i]], edges))
            if k == 0:
                faces.append((A[::-1], [(i, (i + 1) % m) for i in range(m)]))  # start cap, normal -u
            if k == n - 1:
                faces.append((B, [(i, (i + 1) % m) for i in range(m)]))  # end cap, normal +u
    return faces


def joist(p0, p1, depth, u, v, w, seg):
    """Open web joist: two chord bars and a zigzag of round bar webs."""
    faces = []
    chord = prof_rect(1.5, 4.0)
    faces += prism(p0, p1, chord, u, v, w, seg, shift=0.75)
    lo0, lo1 = add(p0, mul(w, depth - 0.75)), add(p1, mul(w, depth - 0.75))
    faces += prism(lo0, lo1, chord, u, v, w, seg, shift=0)
    L = math.sqrt(dot(sub(p1, p0), sub(p1, p0)))
    panel = 8.0
    n = max(1, int(L / panel))
    pts = []
    for i in range(n + 1):
        t = L * i / n
        top = add(p0, add(mul(u, t), mul(w, 1.5)))
        bot = add(p0, add(mul(u, t), mul(w, depth - 1.5)))
        pts.append(top if i % 2 == 0 else bot)
    for a, b in zip(pts, pts[1:]):
        uu, vv, ww = frame(a, b)
        faces += prism(a, b, prof_rect(0.5, 0.5), uu, vv, ww, seg)
    return faces


def box(centre, ex, ny, z, seg=1e9):
    """Axis aligned box, sizes along E, N, Z."""
    p0 = add(centre, [0, 0, -z / 2])
    p1 = add(centre, [0, 0, z / 2])
    u, v, w = [0, 0, 1], [1, 0, 0], [0, 1, 0]
    v = cross(w, u)  # keep the frame right handed
    return prism(p0, p1, prof_rect(ny, ex), u, v, w, seg)


# ------------------------------------------------------------------ load
def num(x, levels):
    """A coordinate: a number, or a level name with an optional +/- offset."""
    if isinstance(x, (int, float)):
        return float(x)
    m = re.match(r"\s*([A-Za-z_][\w]*)\s*(?:([+-])\s*([\d.]+))?\s*$", str(x))
    if not m or m.group(1) not in levels:
        raise ValueError("bad coordinate %r" % x)
    z = float(levels[m.group(1)])
    if m.group(2):
        z += float(m.group(3)) * (1 if m.group(2) == "+" else -1)
    return z


def members(doc):
    """Flatten the YAML into (id, section, from, to, axis, record)."""
    out = []
    for key, axis in GROUPS.items():
        for m in doc.get(key, []):
            out.append((m["id"], section_key(m["section"]), m["from"], m["to"], axis, m))
    t = doc.get("truss")
    if t:
        for part in ("top_chord", "bottom_chord"):
            c = t[part]
            out.append((t["id"] + "-" + part, section_key(c["section"]), c["from"], c["to"], "centre", c))
        for wb in t.get("web", []):
            out.append((wb["id"], section_key(wb["section"]), wb["from"], wb["to"], "centre", wb))
        for p in t.get("purlins", []):
            out.append((p["id"], section_key(p["section"]), p["from"], p["to"], "tos", p))
    return out


def edit(doc, drop=(), scale_z=1.0, scale_plan=1.0):
    """Apply the edits on the data, before anything is drawn."""
    for key in GROUPS:
        doc[key] = [m for m in doc.get(key, []) if m["id"] not in drop]
    t = doc.get("truss")
    if t:
        if t["id"] in drop:
            doc["truss"] = None
        else:
            t["web"] = [w for w in t.get("web", []) if w["id"] not in drop]
            t["purlins"] = [p for p in t.get("purlins", []) if p["id"] not in drop]
    for m in doc.get("girders", []) + doc.get("beams", []):
        if "carries" in m:
            m["carries"] = [c for c in m["carries"] if c not in drop]
    if scale_z != 1.0 or scale_plan != 1.0:
        for k, z in doc["levels"].items():
            doc["levels"][k] = z * scale_z
        for _, _, a, b, _, rec in members(doc):
            for pt in (a, b):
                for i in range(2):
                    pt[i] = pt[i] * scale_plan
                if isinstance(pt[2], (int, float)):
                    pt[2] = pt[2] * scale_z
    return doc


def bolt_count(rec):
    txt = " ".join(str(v) for v in rec.values())
    return sum(int(k) for k in re.findall(r"(\d+)\s*(?:\+\s*\d+\s*)?bolts?", txt))


# ---------------------------------------------------------------- camera
NAMED = {"iso": (225, 35.264), "west": (270, 0), "east": (90, 0),
         "north": (0, 0), "south": (180, 0), "plan": (0, 90)}


def camera(view):
    if view in NAMED:
        az, el = NAMED[view]
    else:
        az, el = (float(x) for x in view.split(","))
    a, e = math.radians(az), math.radians(el)
    c = [math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)]  # towards the camera
    r = cross([0, 0, 1], c)
    if math.sqrt(dot(r, r)) < 1e-6:  # plan view
        r = [1, 0, 0]
    r = norm(r)
    up = norm(cross(c, r))
    return c, r, up


# ----------------------------------------------------------------- render
def build(doc, web_only=(), seg=6.0, bolts=True):
    """Everything to draw: (member id, faces) and bolt dots (id, point, v, section)."""
    levels = doc["levels"]
    solids, dots = [], []
    for mid, sec, a, b, axis, rec in members(doc):
        p0 = [num(x, levels) for x in a]
        p1 = [num(x, levels) for x in b]
        if sec not in SECTIONS:
            print("  no section dims for %s (%s), skipped" % (sec, mid), file=sys.stderr)
            continue
        facing = rec.get("facing")
        u, v, w = frame(p0, p1, facing, rec.get("stem") == "up")
        if SECTIONS[sec][0] == "K":
            polys = prof_rect(1, 4)
            solids.append((mid, joist(p0, p1, rec.get("depth", SECTIONS[sec][1]), u, v, w, seg)))
        else:
            polys, d = profile(sec, mid in web_only)
            shift = d / 2 if axis == "tos" else 0.0
            solids.append((mid, prism(p0, p1, polys, u, v, w, seg, shift)))
        n = bolt_count(rec) if bolts else 0
        if n:
            # a group of dots at the `from` end, rows of 4 down the depth,
            # on the web face that looks at the camera
            for i in range(n):
                if axis == "tos":
                    bw = 2.5 + 1.5 * (i % 4)
                else:
                    bw = 1.5 * (i % 4) - 0.75 * (min(n, 4) - 1)
                p = add(p0, add(mul(w, bw), mul(u, 1.5 + 1.5 * (i // 4))))
                dots.append((mid, p, v, sec))
    # the base plate, the one plate worth drawing
    col = doc.get("column")
    if col:
        m = re.search(r"PL\s*([\d.]+)\s*x\s*([\d.]+)\s*x\s*([\d.]+)", str(col[0].get("base_plate", "")))
        if m:
            t, b1, b2 = (float(x) for x in m.groups())
            z0 = num(col[0]["from"][2], levels)
            solids.append(("base_plate", box([0, 0, z0 - t / 2], b1, b2, t)))
    return solids, dots


def render(solids, dots, view, scale, dst, drop_note=""):
    c, r, up = camera(view)

    def proj(p):
        return (dot(p, r) * scale, -dot(p, up) * scale)

    items = []  # (depth, member, svg)
    for mid, faces in solids:
        for pts, edges in faces:
            n = cross(sub(pts[1], pts[0]), sub(pts[2], pts[0]))
            if dot(n, c) <= 1e-9:
                continue  # back face, or seen edge on
            depth = sum(dot(p, c) for p in pts) / len(pts)
            q = [proj(p) for p in pts]
            d = "M" + " L".join("%.1f %.1f" % xy for xy in q) + " Z"
            e = " ".join("M%.1f %.1f L%.1f %.1f" % (q[i] + q[j]) for i, j in edges)
            items.append((depth, mid, '<path d="%s"/><path class="e" d="%s"/>' % (d, e)))
    for mid, p, v, sec in dots:
        side = 1 if dot(v, c) >= 0 else -1
        p = add(p, mul(v, bolt_face(sec, side)))
        depth = dot(p, c) + 1.0
        x, y = proj(p)
        items.append((depth, mid, '<circle cx="%.1f" cy="%.1f" r="%.1f"/>' % (x, y, 0.45 * scale)))
    items.sort(key=lambda t: t[0])

    xs = [float(v) for _, _, s in items for v in re.findall(r"[ML](-?[\d.]+) ", s)]
    ys = [float(v) for _, _, s in items for v in re.findall(r"[ML]-?[\d.]+ (-?[\d.]+)", s)]
    if not xs:
        raise SystemExit("nothing to draw")
    pad = 6 * scale
    x0, y0, x1, y1 = min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad
    sw = 0.3 * scale
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="%.0f %.0f %.0f %.0f">' % (x0, y0, x1 - x0, y1 - y0),
           '<style>path{fill:#fff;stroke:none}'
           'path.e{fill:none;stroke:#000;stroke-width:%.2f;stroke-linecap:round}circle{fill:#000}</style>' % sw]
    cur = None
    for _, mid, s in items:
        if mid != cur:
            if cur is not None:
                out.append("</g>")
            out.append('<g id="%s">' % mid)
            cur = mid
        out.append(s)
    out.append("</g></svg>")
    open(dst, "w").write("\n".join(out) + "\n")
    print("  %s: view %s, %d members, %d faces, %d bolt dots%s"
          % (dst, view, len(solids), sum(1 for i in items if "<path" in i[2]), len(dots), drop_note))


def main(argv):
    a = list(argv)
    opt = {"--view": "iso", "--scale": "4", "--drop": "", "--web-only": "", "--scale-z": "1", "--scale-plan": "1", "--seg": "6"}
    for k in list(opt):
        if k in a:
            i = a.index(k); opt[k] = a[i + 1]; del a[i:i + 2]
    bolts = "--no-bolts" not in a
    if not bolts:
        a.remove("--no-bolts")
    src, dst = a
    drop = tuple(x for x in opt["--drop"].split(",") if x)
    web_only = tuple(x for x in opt["--web-only"].split(",") if x)
    doc = yaml.safe_load(open(src))
    doc = edit(doc, drop, float(opt["--scale-z"]), float(opt["--scale-plan"]))
    solids, dots = build(doc, web_only, float(opt["--seg"]), bolts)
    note = (", dropped " + ",".join(drop) if drop else "") + (", web only " + ",".join(web_only) if web_only else "")
    render(solids, dots, opt["--view"], float(opt["--scale"]), dst, note)


if __name__ == "__main__":
    main(sys.argv[1:])
