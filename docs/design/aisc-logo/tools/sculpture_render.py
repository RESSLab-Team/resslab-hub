"""Render the sculpture from reference/sculpture.yaml as a line drawing.

  python3 tools/sculpture_render.py reference/sculpture.yaml out.svg
        [--view iso|west|east|north|south|plan|AZ,EL] [--scale 4]
        [--no-bolts] [--no-plates] [--drop 12C1,12D1] [--web-only 5B2,5B1]
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
5. style: black edges, white faces, bolts as black dots laid out on the
   connection plates. One <g> per member, named by its mark.

Connections are drawn from the structured records in the YAML: a plate,
angle, tee or seat between the member end and the face of its support,
sized from the record, so a member never floats. The setback in the
data is real, the hardware fills it.
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


# ------------------------------------------------------------- geometry
class G:
    """One member, resolved: end points, frame, section, profile."""


def web_thickness(sec):
    kind, *dims = SECTIONS[sec]
    if kind in ("I", "C", "T"):
        return dims[2]
    if kind == "2L":
        return 2 * dims[2] + 0.375
    if kind == "RHS":
        return dims[1]
    if kind == "O":
        return dims[0]
    return 4.0  # joist chord


def geometry(doc, web_only=()):
    levels = doc["levels"]
    gs = {}
    for mid, sec, a, b, axis, rec in members(doc):
        if sec not in SECTIONS:
            print("  no section dims for %s (%s), skipped" % (sec, mid), file=sys.stderr)
            continue
        g = G()
        g.id, g.sec, g.axis, g.rec = mid, sec, axis, rec
        g.p0 = [num(x, levels) for x in a]
        g.p1 = [num(x, levels) for x in b]
        g.u, g.v, g.w = frame(g.p0, g.p1, rec.get("facing"), rec.get("stem") == "up")
        g.kind = SECTIONS[sec][0]
        if g.kind == "K":
            g.d = float(rec.get("depth", SECTIONS[sec][1]))
            g.polys = prof_rect(1.5, 4.0)
        else:
            g.polys, g.d = profile(sec, mid in web_only)
        g.sh = g.d / 2 if axis == "tos" else 0.0
        g.tw = web_thickness(sec)
        gs[mid] = g
    return gs


def closest(S, p):
    """Closest point to p on the axis segment of member S."""
    L = math.sqrt(dot(sub(S.p1, S.p0), sub(S.p1, S.p0)))
    t = min(max(dot(sub(p, S.p0), S.u), 0.0), L)
    return add(S.p0, mul(S.u, t))


def support_face(S, direc, override=None):
    """How far the surface of S is from its axis line, in direction direc.
    Across the width of an I or T that is the web, unless `face: flange`
    asks for the flange tips. Otherwise the outline of the section."""
    if isinstance(override, (int, float)):
        return float(override)
    da, db = dot(direc, S.v), dot(direc, S.w)
    if override != "flange" and S.kind in ("I", "T") and abs(da) > 0.9:
        return S.tw / 2
    return max(pa * da + (pb + S.sh) * db for poly in S.polys for pa, pb in poly)


def box3(centre, ay, az, sx, sy, sz):
    """A box: sizes sx, sy, sz along (ay x az), ay, az."""
    v = cross(ay, az)
    return prism(sub(centre, mul(az, sz / 2)), add(centre, mul(az, sz / 2)), prof_rect(sy, sx), az, v, ay, 1e9)


def connections(doc):
    """(member id, record) for every connection in the YAML."""
    out = []
    for key in GROUPS:
        for m in doc.get(key, []):
            if "connection" in m:
                out.append((m["id"], dict(m["connection"])))
            for c in m.get("connections", []):
                out.append((m["id"], c))
    t = doc.get("truss")
    if t:
        for c in t.get("connections", []):
            out.append((t["id"] + "-" + c["member"], c))
    return out


def resolve(g, c, gs):
    """Where a connection sits: the member end, the direction into the
    member, the support face point and the gap between the two. The end
    is the one nearer the support unless `at:` says which. The gap is
    measured along the member's own axis, projected perpendicular to the
    support, so a beam that sits a little above its girder still meets
    the girder web sideways."""
    S = gs.get(c.get("to"))
    if S is None:
        return None
    at = c.get("at")
    if at is None:
        d0 = dot(sub(g.p0, closest(S, g.p0)), sub(g.p0, closest(S, g.p0)))
        d1 = dot(sub(g.p1, closest(S, g.p1)), sub(g.p1, closest(S, g.p1)))
        at = "from" if d0 <= d1 else "to"
    p = g.p0 if at == "from" else g.p1
    inward = g.u if at == "from" else mul(g.u, -1)
    q = closest(S, p)
    direc = sub(inward, mul(S.u, dot(inward, S.u)))  # from the support towards the member
    if math.sqrt(dot(direc, direc)) < 0.1:  # member parallel to its support
        direc = sub(p, q)
    direc = norm(direc)
    dist = dot(sub(p, q), direc)
    face = support_face(S, direc, c.get("face"))
    gap = max(0.0, dist - face)
    return dict(S=S, at=at, p=p, inward=inward, direc=direc, gap=gap, fp=add(q, mul(direc, face)))


def rows_cols(n, cols, span, pitch=3.0):
    """Bolt offsets on a plate: `cols` columns, rows `pitch` apart, the
    rows centred and squeezed to fit `span`."""
    if n <= 0:
        return []
    rows = int(math.ceil(n / cols))
    if rows > 1:
        pitch = min(pitch, (span - 3.0) / (rows - 1))
    out = []
    for i in range(n):
        r, k = divmod(i, cols)
        out.append((k, (r - (rows - 1) / 2) * pitch))
    return out


def web_plate(g, r, plate, n, dots, mid):
    """A plate in the web plane: a shear tab, an angle, a tee, double
    angles. Spans from the support face into the member."""
    t, L, h = plate
    L = max(L, r["gap"] + 1.5)
    lin = L - r["gap"]
    centre = add(add(r["p"], mul(r["inward"], L / 2 - r["gap"])), mul(g.w, g.sh))
    faces = box3(centre, g.w, r["inward"], g.tw + 2 * t, h, L)
    cols = 1 if n <= 4 or lin < 4 else 2
    for k, dw in rows_cols(n, cols, h):
        du = lin / 2 + (k - (cols - 1) / 2) * 3.0
        pt = add(add(r["p"], mul(r["inward"], du)), mul(g.w, g.sh + dw))
        dots.append((mid, pt, g.v, g.tw / 2 + t))
    return faces


def hardware(g, c, r, want_bolts):
    """The solid(s) of one connection and its bolt dots."""
    faces, dots = [], []
    typ = c.get("type", "shear_tab")
    n = int(c.get("bolts", 0)) if want_bolts else 0
    p, inward, gap, mid = r["p"], r["inward"], r["gap"], g.id
    if typ in ("shear_tab", "single_angle", "double_angle", "tee", "bolted_web", "plate"):
        faces += web_plate(g, r, c.get("plate", [0.375, 4.5, g.d - 3]), n, dots, mid)
    elif typ == "end_plate":
        t, wp, hp = c.get("plate", [0.375, 6, g.d - 3])
        th = max(gap, t)
        centre = add(add(p, mul(inward, -th / 2)), mul(g.w, g.sh))
        faces += box3(centre, g.w, inward, wp, hp, th)
        cols = 2 if wp >= 5 else 1
        for k, dw in rows_cols(n, cols, hp):
            dv = (k - (cols - 1) / 2) * (wp - 3.0)
            pt = add(add(add(p, mul(inward, 0.05)), mul(g.v, dv)), mul(g.w, g.sh + dw))
            dots.append((mid, pt, None, 0))
    elif typ == "flange_plates":
        t, wp, L = c.get("plate", [0.5, g.d, 12])
        L = max(L, gap + 3)
        for top in (True, False):
            dw = -t / 2 if top else g.d + t / 2
            centre = add(add(p, mul(inward, L / 2 - gap)), mul(g.w, dw))
            faces += box3(centre, g.w, inward, wp, t, L)
            half = n // 2 if top else n - n // 2
            if half:
                lin = L - gap
                rows = int(math.ceil(half / 2))
                pitch = min(3.0, (lin - 3.0) / max(rows - 1, 1))
                for i in range(half):
                    rr, k = divmod(i, 2)
                    du = 1.5 + rr * pitch
                    dv = (k - 0.5) * (wp - 3.0)
                    pt = add(add(p, mul(inward, du)), mul(g.v, dv))
                    pt = add(pt, mul(g.w, -t if top else g.d + t))
                    dots.append((mid, pt, None, 0))
        wpl = c.get("web_plate")
        if wpl:
            faces += web_plate(g, r, wpl, int(c.get("web_bolts", 0)) if want_bolts else 0, dots, mid)
    elif typ == "welded":
        tab = c.get("tab")
        if tab:
            r0 = dict(r, gap=0.0)
            faces += web_plate(g, r0, tab, n, dots, mid)
    elif typ == "seat":
        t, wp, L = c.get("plate", [0.5, 6, 5])
        L = max(L, gap + 3)
        centre = add(add(p, mul(inward, L / 2 - gap)), mul(g.w, g.d + t / 2))
        faces += box3(centre, g.w, inward, wp, t, L)  # the seat under the bottom flange
        Lc = gap + 3
        centre = add(add(p, mul(inward, Lc / 2 - gap)), mul(g.w, -0.19))
        faces += box3(centre, g.w, inward, wp, 0.375, Lc)  # the top clip
        for i in range(n):
            pt = add(add(add(p, mul(inward, 1.5)), mul(g.v, (i - (n - 1) / 2) * 3.0)), mul(g.w, -0.4))
            dots.append((mid, pt, None, 0))
    elif typ in ("gusset", "pin"):
        t, L, hp = c.get("plate", [0.375, 6, 6])
        L = max(L, gap + 2)
        nrm = cross(r["direc"], g.u)
        if math.sqrt(dot(nrm, nrm)) < 1e-3:
            nrm = g.v
        nrm = norm(nrm)
        across = norm(cross(nrm, r["direc"]))
        centre = add(r["fp"], mul(r["direc"], L / 2))
        faces += box3(centre, across, r["direc"], t, hp, L)
        if c.get("bolts_at") == "face":
            for i in range(n):
                pt = add(add(r["fp"], mul(r["direc"], 1.5)), mul(across, (i - (n - 1) / 2) * 3.0))
                dots.append((mid, pt, nrm, t / 2))
        else:
            for i in range(n):
                pt = add(p, mul(inward, 1.5 + 3.0 * i))
                dots.append((mid, pt, nrm, max(g.tw / 2, t / 2) + 0.05))
    return faces, dots


def splice_hardware(sp, gs, levels, want_bolts):
    faces, dots = [], []
    A, B = (gs.get(x) for x in sp.get("between", [None, None]))
    if A is None or B is None:
        return faces, dots
    sid = "splice_" + sp["id"].replace("/", "_")
    if "z" in sp:  # column splice, shafts vertical: u = Z, v = E, w = N
        z = num(sp["z"], levels)
        P = [A.p0[0], A.p0[1], z]
        dmax = max(A.d, B.d)
        for pl in sp.get("plates", []):
            t, w, h = pl["size"]
            n = int(pl.get("bolts", 0)) if want_bolts else 0
            on = pl["where"]
            if on in ("north_flange", "south_flange"):
                sgn = 1 if on == "north_flange" else -1
                centre = add(P, mul(A.w, sgn * (dmax / 2 + t / 2)))
                faces += box3(centre, A.w, A.u, w, t, h)
                for k, dz in rows_cols(n, 2, h):
                    pt = add(add(centre, mul(A.v, (k - 0.5) * (w - 3.0))), mul(A.u, dz))
                    dots.append((sid, add(pt, mul(A.w, sgn * t / 2)), None, 0))
            elif on == "web":
                tw = min(A.tw, B.tw)
                faces += box3(P, A.w, A.u, tw + 2 * t, w, h)
                for k, dz in rows_cols(n, 2, h):
                    pt = add(add(P, mul(A.w, (k - 0.5) * (w - 3.5))), mul(A.u, dz))
                    dots.append((sid, pt, A.v, tw / 2 + t))
            elif on == "cap":
                centre = add(P, mul(A.u, -t / 2))
                faces += box3(centre, A.w, A.u, w, h, t)
                for i in range(n):
                    dv = (w / 2 - 1.2) * (1 if i % 2 else -1)
                    dw = (h / 2 - 1.2) * (1 if i // 2 else -1)
                    pt = add(add(P, mul(A.v, dv)), mul(A.w, dw))
                    dots.append((sid, pt, None, 0))
    else:  # beam splice, in the frame of the first piece
        P = mul(add(A.p1, B.p0), 0.5)
        for pl in sp.get("plates", []):
            t, w, L = pl["size"]
            n = int(pl.get("bolts", 0)) if want_bolts else 0
            on = pl["where"]
            if on in ("top_flange", "bottom_flange"):
                top = on == "top_flange"
                dw = -t / 2 if top else A.d + t / 2
                centre = add(P, mul(A.w, dw))
                faces += box3(centre, A.w, A.u, w, t, L)
                per_side = n // 2
                for side in (-1, 1):
                    for k, du in rows_cols(per_side, 2, L / 2 - 1.5):
                        pt = add(add(P, mul(A.u, side * (L / 4 + du))), mul(A.v, (k - 0.5) * (w - 3.0)))
                        dots.append((sid, add(pt, mul(A.w, -t if top else A.d + t)), None, 0))
            elif on == "web":
                centre = add(P, mul(A.w, A.sh))
                faces += box3(centre, A.w, A.u, A.tw + 2 * t, L, w)
                per_side = n // 2
                for side in (-1, 1):
                    for k, dz in rows_cols(per_side, 2, L):
                        pt = add(add(P, mul(A.u, side * (1.75 + k * 3.0))), mul(A.w, A.sh + dz))
                        dots.append((sid, pt, A.v, A.tw / 2 + t))
    return faces, dots


def build(doc, web_only=(), seg=6.0, bolts=True, plates=True):
    """Everything to draw: (id, faces) and bolt dots (id, point, axis, half)."""
    levels = doc["levels"]
    gs = geometry(doc, web_only)
    solids, dots = [], []
    conns = []
    for mid, c in connections(doc):
        g = gs.get(mid)
        if g is None:
            continue
        r = resolve(g, c, gs)
        if r is None:
            print("  %s: support %s not found" % (mid, c.get("to")), file=sys.stderr)
            continue
        # a welded end runs to the support face
        if c.get("type") in ("welded", "bearing") and abs(dot(r["direc"], g.u)) > 0.95 and r["gap"] > 0:
            if r["at"] == "from":
                g.p0 = r["fp"]
            else:
                g.p1 = r["fp"]
            r = resolve(g, c, gs)
        conns.append((g, c, r))
    for g in gs.values():
        if g.kind == "K":
            solids.append((g.id, joist(g.p0, g.p1, g.d, g.u, g.v, g.w, seg)))
        else:
            solids.append((g.id, prism(g.p0, g.p1, g.polys, g.u, g.v, g.w, seg, g.sh)))
    if plates:
        for g, c, r in conns:
            f, d = hardware(g, c, r, bolts)
            if f:
                solids.append((g.id + "-conn-" + r["at"], f))
            dots += d
        for sp in doc.get("splices", []):
            f, d = splice_hardware(sp, gs, levels, bolts)
            if f:
                solids.append(("splice_" + sp["id"].replace("/", "_"), f))
            dots += d
    # the base plate, the one plate outside the connections worth drawing
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
    for mid, p, axis, half in dots:
        if axis is not None:  # on whichever face looks at the camera
            side = 1 if dot(axis, c) >= 0 else -1
            p = add(p, mul(axis, side * half))
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
    plates = "--no-plates" not in a
    if not plates:
        a.remove("--no-plates")
    src, dst = a
    drop = tuple(x for x in opt["--drop"].split(",") if x)
    web_only = tuple(x for x in opt["--web-only"].split(",") if x)
    doc = yaml.safe_load(open(src))
    doc = edit(doc, drop, float(opt["--scale-z"]), float(opt["--scale-plan"]))
    solids, dots = build(doc, web_only, float(opt["--seg"]), bolts, plates)
    note = (", dropped " + ",".join(drop) if drop else "") + (", web only " + ",".join(web_only) if web_only else "")
    render(solids, dots, opt["--view"], float(opt["--scale"]), dst, note)


if __name__ == "__main__":
    main(sys.argv[1:])
