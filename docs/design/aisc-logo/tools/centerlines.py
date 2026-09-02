"""Collapse the drawing's members to single centre lines.

A member in the elevation is drawn as two long parallel lines, its flanges.
This finds those pairs and replaces each one by a single line down the
middle, so a beam becomes a stroke instead of an outline. What comes out is
the most reduced form of the drawing that is still the drawing: about two
dozen lines that keep the frame, the truss and the brace.

  python3 tools/centerlines.py <in.svg> <out.svg>
        [--gap 420] [--min-len 400] [--width 110]

--gap is how far apart two lines may be and still count as one member
(plot units, the drawing is 2446 wide, a girder is about 400 deep).
--min-len drops the short leftovers. --width is the output stroke.

Feed it the skeleton, not the full drawing:

  python3 tools/reweight.py in.svg skel.svg --heavy 10 --min-len 50 \\
      --only-heavy
  python3 tools/centerlines.py skel.svg mark.svg

Do not expect this to give a 16 px icon. It does not, and neither does any
other reduction of this drawing: at that size the members are thinner than
a pixel and the whole thing greys out. It reads from about 32 px. The tab
icon has to be a purpose drawn glyph, see favicon/.
"""
import importlib.util
import os
import sys
import xml.etree.ElementTree as ET

SVG = "http://www.w3.org/2000/svg"
HERE = os.path.dirname(os.path.abspath(__file__))


def load_hand2logo():
    """Reuse the pair merging that is already written and tuned there."""
    path = os.path.join(HERE, "hand2logo.py")
    spec = importlib.util.spec_from_file_location("hand2logo", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(src, dst, gap, min_len, width, grid24=False, color=None):
    h = load_hand2logo()
    root = ET.parse(src).getroot()
    vb = root.get("viewBox")

    segs = []
    for el in root.iter("{%s}path" % SVG):
        d = el.get("d")
        if not d:
            continue
        for ring in h.parse_d(d):
            for k in range(len(ring) - 1):
                p, q = ring[k], ring[k + 1]
                if h.dist(p, q) > 0.01:
                    segs.append((p, q))

    lines = h.coalesce_collinear(segs)
    _, centres = h.merge_parallel(lines, max_gap=gap)
    centres = [(p, q) for p, q in centres if h.dist(p, q) >= min_len]

    fmt = "M%.0f %.0fL%.0f %.0f"
    if grid24:
        # square the drawing into a 0 0 24 24 box, the grid the favicon
        # glyphs use, so the same build script can consume it. The drawing
        # is not square, so it is centred and the stroke scales with it.
        x0, y0, w, ht = [float(v) for v in vb.split()]
        side = max(w, ht)
        cx, cy = x0 + w / 2, y0 + ht / 2
        k = 24.0 / side

        def tx(p):
            return ((p[0] - cx) * k + 12.0, (p[1] - cy) * k + 12.0)

        centres = [(tx(p), tx(q)) for p, q in centres]
        width = "%.2f" % (float(width) * k)
        vb, fmt = "0 0 24 24", "M%.2f %.2fL%.2f %.2f"

    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="%s">' % vb,
           '<g fill="none" stroke="%s" stroke-width="%s" '
           'stroke-linecap="round" stroke-linejoin="round">'
           % (color or "currentColor", width)]
    for p, q in centres:
        out.append('<path d="%s"/>' % (fmt % (p[0], p[1], q[0], q[1])))
    out.append("</g></svg>")
    open(dst, "w").write("\n".join(out) + "\n")

    print("  %-26s %d members from %d segments"
          % (os.path.basename(dst), len(centres), len(segs)))


if __name__ == "__main__":
    a = sys.argv[1:]
    gap, min_len, width = 420.0, 400.0, "110"
    grid24 = "--grid24" in a
    if grid24:
        a.remove("--grid24")
    color = None
    if "--color" in a:
        i = a.index("--color")
        color = a[i + 1]
        del a[i:i + 2]
    for flag, conv in (("--gap", float), ("--min-len", float),
                       ("--width", str)):
        if flag in a:
            i = a.index(flag)
            val = conv(a[i + 1])
            del a[i:i + 2]
            if flag == "--gap":
                gap = val
            elif flag == "--min-len":
                min_len = val
            else:
                width = val
    main(a[0], a[1], gap, min_len, width, grid24, color)
