"""Give the cleaned drawing a two weight line hierarchy.

The cleaned SVG draws every structural line at width 5 and the small
hardware at width 2. A real technical drawing is not flat like that: the
members that carry the shape are drawn heavy and the detail stays light.

This promotes the LONG lines of the width 5 layer to a heavier stroke and
leaves everything else alone, so bolts, weld marks, small clips and short
plate edges keep their weight.

  python3 tools/reweight.py <in.svg> <out.svg> [--heavy 11] [--min-len 150]
                            [--only-heavy] [--from-width 5]

--from-width is the layer to promote. The cleaned E2 drawing is 5, but the
plates that cad2logo writes are 7, and the isometric lives in a coordinate
space about 2.9x bigger than E2, so its lengths and widths scale with it.

--only-heavy throws away everything that was NOT promoted, so what is left
is the skeleton of the main members. That is the small sizes version: at
32 px and under the fine layer is not detail any more, it is grey haze on
top of the shape.

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
TARGET = 5.0          # default layer to reweight, see --from-width


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


def collect(node, width, stroke, out, target=TARGET):
    """Walk the tree carrying the inherited stroke width and colour."""
    for el in node:
        w = el.get("stroke-width")
        w = float(w) if w else width
        s = el.get("stroke", stroke)
        if el.tag == "{%s}path" % SVG:
            # only the plain stroked lines of the target layer are candidates
            if s != "none" and el.get("fill", "none") == "none" \
                    and abs(w - target) < 1e-6:
                out.append(el)
        else:
            collect(el, w, s, out, target)


def split_subpaths(node):
    """One path per M subpath.

    cad2logo writes a whole plate as a single path with thousands of M
    segments in it. Nothing can be weighed per line until they are split,
    so do it in place before collecting. Files that are already one path
    per line (the cleaned drawing) come through untouched."""
    n = 0
    for parent in node.iter():
        for i, el in reversed(list(enumerate(parent))):
            if el.tag != "{%s}path" % SVG:
                continue
            d = el.get("d") or ""
            parts = [s for s in re.split(r"(?=[Mm])", d) if s.strip()]
            if len(parts) < 2:
                continue
            parent.remove(el)
            for part in reversed(parts):
                new = ET.Element("{%s}path" % SVG)
                for k, v in el.attrib.items():
                    if k != "d":
                        new.set(k, v)
                new.set("d", part.strip())
                parent.insert(i, new)
            n += len(parts) - 1
    return n


def prune(node, keep):
    """Drop every path that is not in keep, then every group left empty."""
    for el in list(node):
        if el.tag == "{%s}path" % SVG:
            if id(el) not in keep:
                node.remove(el)
        else:
            prune(el, keep)
            if len(el) == 0:
                node.remove(el)


def main(src, dst, heavy, min_len, only_heavy=False, target=TARGET):
    ET.register_namespace("", SVG)
    tree = ET.parse(src)
    added = split_subpaths(tree.getroot())
    if added:
        print("  split %d subpaths into their own <path>" % added)
    cand = []
    collect(tree.getroot(), target, "currentColor", cand, target)
    if not cand:
        sys.exit("%s has no width %s lines to work on. Check --from-width,\n"
                 "or, if it is already a reweighted file, run this on the\n"
                 "source drawing instead with the same options."
                 % (src, target))

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

    if only_heavy:
        if not any(is_heavy):
            sys.exit("--only-heavy would keep nothing: no line in %s reaches\n"
                     "--min-len %s. Lower it, or check you are running this\n"
                     "on the source drawing and not on an already\n"
                     "reweighted file." % (src, min_len))
        keep = set(id(el) for el, h in zip(cand, is_heavy) if h)
        prune(tree.getroot(), keep)

    tree.write(dst, encoding="UTF-8", xml_declaration=True)
    print("  %-30s heavy=%-4s min-len=%-6s %d of %d lines promoted"
          % (dst.rsplit("/", 1)[-1], heavy, min_len, sum(is_heavy), len(cand)))


if __name__ == "__main__":
    a = sys.argv[1:]
    heavy, min_len, target = "11", 150.0, TARGET
    if "--from-width" in a:
        i = a.index("--from-width")
        target = float(a[i + 1])
        del a[i:i + 2]
    only_heavy = "--only-heavy" in a
    if only_heavy:
        a.remove("--only-heavy")
    if "--heavy" in a:
        heavy = a.pop(a.index("--heavy") + 1); a.remove("--heavy")
    if "--min-len" in a:
        min_len = float(a.pop(a.index("--min-len") + 1)); a.remove("--min-len")
    main(a[0], a[1], heavy, min_len, only_heavy, target)
