"""Give the cleaned drawing a two weight line hierarchy.

The cleaned SVG draws every structural line at width 5 and the small
hardware at width 2. A real technical drawing is not flat like that: the
members that carry the shape are drawn heavy and the detail stays light.

This promotes the LONG lines of the width 5 layer to a heavier stroke and
leaves everything else alone, so bolts, weld marks, small clips and short
plate edges keep their weight.

  python3 tools/reweight.py <in.svg> <out.svg> [--heavy 11] [--min-len 150]

A path is long when its own length reaches --min-len. A short path is
promoted too when both of its ends land on the end of a promoted path:
that is the end cap of a member, and leaving it thin puts a visible notch
at each end of every beam.

The width is set on each path in place, nothing is moved in the tree. An
earlier version rebuilt the groups and dropped every structural line into
the fill group, which has stroke="none", so the whole drawing went blank.
"""
import math
import re
import sys
import xml.etree.ElementTree as ET

SVG = "http://www.w3.org/2000/svg"
TOK = re.compile(r"([MmHhVvLlZz])|(-?\d*\.?\d+(?:[eE]-?\d+)?)")
JOIN_TOL = 1.5
TARGET = 5.0          # the layer we reweight, everything else is left alone


def parse_d(d):
    """-> list of point lists (the optimizer emits m/h/v/l/z, relative)."""
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
                    cur.append((sx, sy))
                    rings.append(cur)
                    x, y = sx, sy
                    cur = []
                continue
        if cmd in "mM":
            if cmd == "m":
                x += toks[i]; y += toks[i + 1]
            else:
                x, y = toks[i], toks[i + 1]
            i += 2
            if cur:
                rings.append(cur)
            cur = [(x, y)]; sx, sy = x, y
            cmd = "l" if cmd == "m" else "L"
        elif cmd == "l":
            x += toks[i]; y += toks[i + 1]; i += 2; cur.append((x, y))
        elif cmd == "L":
            x, y = toks[i], toks[i + 1]; i += 2; cur.append((x, y))
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


def path_length(rings):
    return sum(math.hypot(r[k + 1][0] - r[k][0], r[k + 1][1] - r[k][1])
               for r in rings for k in range(len(r) - 1))


def ends(rings):
    return [p for r in rings if len(r) >= 2 for p in (r[0], r[-1])]


def collect(node, width, stroke, out):
    """Walk the tree carrying the inherited stroke width and colour."""
    for el in node:
        w = el.get("stroke-width")
        w = float(w) if w else width
        s = el.get("stroke", stroke)
        if el.tag == "{%s}path" % SVG:
            # only the plain stroked lines of the target layer are candidates
            if s != "none" and el.get("fill", "none") == "none" \
                    and abs(w - TARGET) < 1e-6:
                out.append(el)
        else:
            collect(el, w, s, out)


def main(src, dst, heavy, min_len):
    ET.register_namespace("", SVG)
    tree = ET.parse(src)
    cand = []
    collect(tree.getroot(), TARGET, "currentColor", cand)

    rings = [parse_d(el.get("d")) for el in cand]
    lens = [path_length(r) for r in rings]
    is_heavy = [ln >= min_len for ln in lens]

    # end caps: a short path with both ends on the end of a heavy path closes
    # a member, promote it so the beam does not neck in at its tip
    for _ in range(2):
        pts = set()
        for i, r in enumerate(rings):
            if is_heavy[i]:
                for p in ends(r):
                    pts.add((round(p[0] / JOIN_TOL), round(p[1] / JOIN_TOL)))
        added = 0
        for i, r in enumerate(rings):
            if is_heavy[i] or lens[i] < 3.0:
                continue
            e = ends(r)
            if len(e) != 2:
                continue
            hit = 0
            for p in e:
                cx, cy = round(p[0] / JOIN_TOL), round(p[1] / JOIN_TOL)
                if any((cx + dx, cy + dy) in pts
                       for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                    hit += 1
            if hit == 2:
                is_heavy[i] = True
                added += 1
        if not added:
            break

    for el, h in zip(cand, is_heavy):
        if h:
            el.set("stroke-width", heavy)

    tree.write(dst, encoding="UTF-8", xml_declaration=True)
    print("  %-30s heavy=%-4s min-len=%-6s %d of %d lines promoted"
          % (dst.rsplit("/", 1)[-1], heavy, min_len, sum(is_heavy), len(cand)))


if __name__ == "__main__":
    a = sys.argv[1:]
    heavy, min_len = "11", 150.0
    if "--heavy" in a:
        heavy = a.pop(a.index("--heavy") + 1); a.remove("--heavy")
    if "--min-len" in a:
        min_len = float(a.pop(a.index("--min-len") + 1)); a.remove("--min-len")
    main(a[0], a[1], heavy, min_len)
