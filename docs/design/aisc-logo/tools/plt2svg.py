#!/usr/bin/env python3
"""Decode SDS2 HPGL2 .plt plot files to SVG.

Handles the subset these plots use: PE (encoded polylines), PM/FP polygons,
CI circles, AA/AR arcs, SP pen select, PU/PD/PA plain moves, SC scaling.
Text is stroked/filled geometry in the stream (no LB), so it comes along.
"""
import math
import re
import sys


def extract_hpgl(data: bytes) -> bytes:
    """Concatenate HPGL2 spans (between ESC%0B and the next ESC)."""
    out = []
    i = 0
    while True:
        j = data.find(b"\x1b%0B", i)
        if j < 0:
            break
        j += 4
        k = data.find(b"\x1b", j)
        if k < 0:
            k = len(data)
        out.append(data[j:k])
        i = k
    return b"".join(out)


class PE:
    """Iterator over PE-encoded values."""

    def __init__(self, buf, pos):
        self.buf = buf
        self.pos = pos
        self.base32 = False

    def peek_flag(self):
        c = self.buf[self.pos]
        return chr(c) if c in b":<>=7" else None

    def next_value(self):
        n = 0
        shift = 0
        while True:
            c = self.buf[self.pos]
            self.pos += 1
            if self.base32:
                if 63 <= c <= 94:
                    n |= (c - 63) << shift
                    shift += 5
                elif 95 <= c <= 126:
                    n |= (c - 95) << shift
                    return n
                else:
                    raise ValueError(f"bad PE digit {c} at {self.pos}")
            else:
                if 63 <= c <= 126:
                    n |= (c - 63) << shift
                    shift += 6
                elif 191 <= c <= 254:
                    n |= (c - 191) << shift
                    return n
                else:
                    raise ValueError(f"bad PE digit {c} at {self.pos}")

    def decode_int(self, n, frac):
        v = -(n >> 1) if (n & 1) else (n >> 1)
        return v / (1 << frac)


class Plot:
    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.pen = 0
        self.frac = 0
        self.polylines = []  # (pen, [pts])
        self.polygons = []  # (pen, [[pts], [pts], ...])
        self.circles = []  # (pen, cx, cy, r)
        self.in_pm = False
        self.pm_paths = []
        self.pm_cur = []
        self.cur_line = None

    def moveto(self, x, y):
        self.x, self.y = x, y
        if self.in_pm:
            if self.pm_cur:
                self.pm_paths.append(self.pm_cur)
            self.pm_cur = [(x, y)]
        else:
            self.cur_line = None

    def lineto(self, x, y):
        if self.in_pm:
            if not self.pm_cur:
                self.pm_cur = [(self.x, self.y)]
            self.pm_cur.append((x, y))
        else:
            if self.cur_line is None:
                self.cur_line = [(self.x, self.y)]
                self.polylines.append((self.pen, self.cur_line))
            self.cur_line.append((x, y))
        self.x, self.y = x, y

    def pm(self, arg):
        if arg == 0:
            self.in_pm = True
            self.pm_paths = []
            self.pm_cur = [(self.x, self.y)]
        elif arg == 1:
            if self.pm_cur:
                self.pm_paths.append(self.pm_cur)
            self.pm_cur = [(self.x, self.y)]
        else:  # 2: close and exit
            if self.pm_cur:
                self.pm_paths.append(self.pm_cur)
            self.pm_cur = []
            self.in_pm = False

    def fill(self):
        if self.pm_paths:
            self.polygons.append((self.pen, [p[:] for p in self.pm_paths]))

    def edge(self):
        for p in self.pm_paths:
            if len(p) > 1:
                self.polylines.append((self.pen, p[:] + [p[0]]))

    def circle(self, r):
        self.circles.append((self.pen, self.x, self.y, r))

    def arc(self, cx, cy, ang):
        a0 = math.atan2(self.y - cy, self.x - cx)
        r = math.hypot(self.x - cx, self.y - cy)
        steps = max(2, int(abs(ang) / 5))
        pts = []
        for i in range(steps + 1):
            a = a0 + math.radians(ang) * i / steps
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        for px, py in pts[1:]:
            self.lineto(px, py)


def parse(hp: bytes, plot: Plot):
    i = 0
    n = len(hp)
    num_re = re.compile(rb"[-+0-9.,\s]+")
    while i < n - 1:
        cmd = hp[i : i + 2]
        if cmd == b"PE":
            i += 2
            pe = PE(hp, i)
            pen_up = False
            absolute = False
            try:
                while pe.buf[pe.pos : pe.pos + 1] != b";":
                    c = pe.buf[pe.pos]
                    if c == 0x37:  # '7'
                        pe.base32 = True
                        pe.pos += 1
                        continue
                    if c == 0x3A:  # ':'
                        pe.pos += 1
                        plot.pen = int(pe.decode_int(pe.next_value(), 0))
                        continue
                    if c == 0x3C:  # '<'
                        pen_up = True
                        pe.pos += 1
                        continue
                    if c == 0x3E:  # '>'
                        pe.pos += 1
                        plot.frac = int(pe.decode_int(pe.next_value(), 0))
                        continue
                    if c == 0x3D:  # '='
                        absolute = True
                        pe.pos += 1
                        continue
                    dx = pe.decode_int(pe.next_value(), plot.frac)
                    dy = pe.decode_int(pe.next_value(), plot.frac)
                    if absolute:
                        tx, ty = dx, dy
                        absolute = False
                    else:
                        tx, ty = plot.x + dx, plot.y + dy
                    if pen_up:
                        plot.moveto(tx, ty)
                        pen_up = False
                    else:
                        plot.lineto(tx, ty)
            except (ValueError, IndexError) as e:
                print("PE abort:", e, file=sys.stderr)
            i = pe.pos + 1
            continue
        # plain commands with numeric args
        if cmd in (b"PM", b"FP", b"EP", b"CI", b"SP", b"PU", b"PD", b"PA", b"AA", b"AR", b"SC", b"IP", b"PW"):
            m = num_re.match(hp, i + 2)
            args_b = m.group(0) if m else b""
            j = i + 2 + len(args_b)
            args = [float(a) for a in re.split(rb"[,\s]+", args_b.strip()) if a]
            if cmd == b"PM":
                plot.pm(int(args[0]) if args else 0)
            elif cmd == b"FP":
                plot.fill()
            elif cmd == b"EP":
                plot.edge()
            elif cmd == b"CI":
                if args:
                    plot.circle(args[0])
            elif cmd == b"SP":
                if args:
                    plot.pen = int(args[0])
            elif cmd in (b"PU", b"PA", b"PD"):
                pts = list(zip(args[0::2], args[1::2]))
                for k, (x, y) in enumerate(pts):
                    if cmd == b"PD" or (cmd == b"PA" and k > 0):
                        plot.lineto(x, y)
                    else:
                        plot.moveto(x, y)
            elif cmd == b"AA":
                if len(args) >= 3:
                    plot.arc(args[0], args[1], args[2])
            elif cmd == b"AR":
                if len(args) >= 3:
                    plot.arc(plot.x + args[0], plot.y + args[1], args[2])
            i = j
            if i < n and hp[i : i + 1] == b";":
                i += 1
            continue
        i += 1


def to_svg(plot: Plot, out_path, stroke_w=4.0):
    xs = []
    ys = []
    for _, pts in plot.polylines:
        for x, y in pts:
            xs.append(x)
            ys.append(y)
    for _, paths in plot.polygons:
        for p in paths:
            for x, y in p:
                xs.append(x)
                ys.append(y)
    for _, cx, cy, r in plot.circles:
        xs += [cx - r, cx + r]
        ys += [cy - r, cy + r]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    w, h = x1 - x0, y1 - y0

    def tx(x):
        return round(x - x0, 1)

    def ty(y):
        return round(y - y0, 1)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}">'
        f'<g fill="none" stroke="#000" stroke-width="{stroke_w}" '
        'stroke-linecap="round" stroke-linejoin="round">'
    ]
    for _, pts in plot.polylines:
        d = f"M{tx(pts[0][0])} {ty(pts[0][1])}" + "".join(
            f"L{tx(x)} {ty(y)}" for x, y in pts[1:]
        )
        parts.append(f'<path d="{d}"/>')
    for _, cx, cy, r in plot.circles:
        parts.append(f'<circle cx="{tx(cx)}" cy="{ty(cy)}" r="{r:.1f}"/>')
    parts.append('</g><g fill="#000" stroke="none" fill-rule="evenodd">')
    for _, paths in plot.polygons:
        d = ""
        for p in paths:
            if len(p) < 2:
                continue
            d += f"M{tx(p[0][0])} {ty(p[0][1])}" + "".join(
                f"L{tx(x)} {ty(y)}" for x, y in p[1:]
            ) + "Z"
        if d:
            parts.append(f'<path d="{d}"/>')
    parts.append("</g></svg>")
    with open(out_path, "w") as f:
        f.write("\n".join(parts))
    print(
        f"{out_path}: bbox {w:.0f}x{h:.0f}, {len(plot.polylines)} polylines, "
        f"{len(plot.polygons)} polygons, {len(plot.circles)} circles"
    )


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    data = open(src, "rb").read()
    plot = Plot()
    parse(extract_hpgl(data), plot)
    to_svg(plot, dst)
