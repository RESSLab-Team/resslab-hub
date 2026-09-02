"""Draw an elevation of the sculpture from reference/sculpture.yaml.

  python3 tools/sculpture_draw.py reference/sculpture.yaml out.svg [--view west]
        [--scale 4] [--no-bolts] [--drop 12C1,12D1]

--view west|east|north|south picks the camera (west is the logo view,
E2 Section 1). --drop removes members by id before drawing, which is
the quick way to try "remove the pipe post" or "remove the rod".
--no-bolts leaves out the bolt marks.

This is a proof that the YAML holds the whole shape, not a logo tool:
members are drawn as their outline (depth hung under the TOS line for
beams, width about the centre line for columns and braces), bolt groups
as small squares at the connection. No plates, no welds, no hidden lines.
"""
import re
import sys
import yaml

VIEWS = {  # horizontal axis picker: (index into [E,N,Z], sign)
    "west": (1, -1),   # N to the left
    "east": (1, 1),
    "north": (0, -1),  # E to the left
    "south": (0, 1),
}

# section width (in) seen when a member is viewed across its web, by family
WIDTH = {"W12x96": 12.2, "W12x53": 10.0, "W10x33": 8.0, "HSS4x4x1/4": 4,
         "HSS6x4x1/4": 4, "PIPE 4 STD": 4.5, "WT4x14": 6.5, "WT4x12": 6.5,
         "WT4x9": 4.0, "RB3/4": 0.75, "12K3": 2.5, "C8x11.5": 2.25}


def depth_of(sec):
    if sec.startswith(("W", "C", "HSS", "S")):
        try:
            return float(sec.split("x")[0].lstrip("WCHSST"))
        except ValueError:
            pass
    return WIDTH.get(sec, 3.0)


def members(doc):
    out = []
    for key in ("column", "girders", "beams", "posts", "braces", "joists"):
        for m in doc.get(key, []):
            axis = "tos" if key in ("girders", "beams", "joists") else "centre"
            out.append((m["id"], m["section"], m["from"], m["to"], axis, m))
    t = doc["truss"]
    out.append((t["id"] + "-top", t["top_chord"]["section"], t["top_chord"]["from"], t["top_chord"]["to"], "centre", {}))
    out.append((t["id"] + "-bot", t["bottom_chord"]["section"], t["bottom_chord"]["from"], t["bottom_chord"]["to"], "centre", {}))
    for w in t["web"]:
        out.append((w["id"], w["section"], w["from"], w["to"], "centre", {}))
    for p in t["purlins"]:
        out.append((p["id"], p["section"], p["from"], p["to"], "tos", {}))
    return out


def main(src, dst, view="west", scale=4.0, bolts=True, drop=()):
    doc = yaml.safe_load(open(src))
    hi, sign = VIEWS[view]
    ms = [m for m in members(doc) if m[0] not in drop and m[0].split("-")[0] not in drop]

    def px(p):
        return (sign * p[hi] * scale, -p[2] * scale)

    shapes = []
    for mid, sec, a, b, axis, rec in ms:
        d = rec.get("depth", depth_of(sec))
        (x1, y1), (x2, y2) = px(a), px(b)
        if abs(x1 - x2) < 0.5 and abs(y1 - y2) < 0.5:
            continue  # seen end on, skip
        if axis == "tos":
            top, bot = 0, d * scale
        else:
            top, bot = -d * scale / 2, d * scale / 2
        if abs(y1 - y2) < 1e-6:  # horizontal member: rectangle hung from the line
            xa, xb = sorted((x1, x2))
            shapes.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f"><title>%s %s</title></rect>'
                          % (xa, y1 + top, xb - xa, bot - top, mid, sec))
        elif abs(x1 - x2) < 1e-6:  # vertical member: width about the line
            # a column shaft shows its depth from E or W, its flange width
            # from N or S (the flanges face N and S)
            if "width" in rec:
                w = (rec["depth"] if hi == 1 else rec["width"]) * scale
            else:
                w = WIDTH.get(sec, min(d, 6)) * scale
            ya, yb = sorted((y1, y2))
            shapes.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f"><title>%s %s</title></rect>'
                          % (x1 - w / 2, ya, w, yb - ya, mid, sec))
        else:  # sloping: thick line
            shapes.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke-width="%.1f"><title>%s %s</title></line>'
                          % (x1, y1, x2, y2, min(d, 4) * scale, mid, sec))

    marks = []
    if bolts:
        for key in ("girders", "beams", "posts", "braces"):
            for m in doc.get(key, []):
                if m["id"] in drop:
                    continue
                txt = " ".join(str(v) for v in m.values())
                n = sum(int(k) for k in re.findall(r"(\d+)\s*(?:\+\s*\d+\s*)?bolts?", txt))
                if n:
                    x, y = px(m["from"])
                    s = 1.2 * scale
                    marks.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f"><title>%s: %d bolts</title></rect>'
                                 % (x - s / 2, y + 2 * scale, s, s, m["id"], n))

    pad = 12 * scale
    w, h = 110 * scale + 2 * pad, 110 * scale + 2 * pad
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="%.0f %.0f %.0f %.0f">' % (-55 * scale - pad, -108 * scale - pad, w, h),
           '<g fill="none" stroke="#000" stroke-width="%.1f" stroke-linejoin="round">' % (0.35 * scale)]
    out += shapes
    out.append('</g><g fill="#000" stroke="none">')
    out += marks
    out.append("</g></svg>")
    open(dst, "w").write("\n".join(out) + "\n")
    print("  %s: %s view, %d members, %d bolt groups%s" % (dst, view, len(shapes), len(marks),
          ", dropped " + ",".join(drop) if drop else ""))


if __name__ == "__main__":
    a = sys.argv[1:]
    view, scale, bolts, drop = "west", 4.0, True, ()
    if "--view" in a:
        i = a.index("--view"); view = a[i + 1]; del a[i:i + 2]
    if "--scale" in a:
        i = a.index("--scale"); scale = float(a[i + 1]); del a[i:i + 2]
    if "--no-bolts" in a:
        a.remove("--no-bolts"); bolts = False
    if "--drop" in a:
        i = a.index("--drop"); drop = tuple(a[i + 1].split(",")); del a[i:i + 2]
    main(a[0], a[1], view, scale, bolts, drop)
