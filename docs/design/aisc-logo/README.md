# AISC steel sculpture logo tools

Scripts that turn the AISC steel sculpture shop drawings into logo
candidates for the hub (issue #263). The drawings and every SVG derived
from them are AISC copyright, so they stay out of git (see `.gitignore`)
and live only on local machines. Only the scripts and the hand drawn
favicon glyphs are committed.

Pipeline, in order:

- `tools/plt2svg.py` decodes an HPGL2 `.plt` pen plot (the only true
  vector export in the official plans package) into a full sheet SVG.
- `tools/cad2logo.py` builds clean one-ink plates per view: filled pen
  quads collapsed back to centerline strokes, dimensions, text and
  callouts dropped, bolts as solid dots.
- `tools/cad2full.py` builds full plates (everything except text) as
  layered Inkscape files, for manual cleaning.
- `tools/hand2logo.py` reads the hand-trimmed drawing and builds the
  outputs: faithful (centerline strokes, width 5, hardware at width 2,
  all the detail kept, this is the logo) and favicon (collinear fragments
  joined, close parallel pairs merged, small hardware dropped, every bolt
  replaced by one simple mark: a circle when the symbol is about round, a
  rectangle when it is long). The favicon comes in two styles, outline
  and filled, to compare. View e2 only, the 2D one dlignos picked in #263.

**The shipping artwork is downstream of all this.** Pierre cleaned the tool
output by hand (the detail callout balloons and the zigzag break lines are
gone, they are drawing notation and not structure) and ran it through an SVG
optimizer:

- `hand-logo-e2-cleaned-optimized.svg` (218 kB, 6911 lines) is the logo.
- `hand-logo-e2-favicon-cleaned.svg` (39 kB, 1117 lines) is the same drawing
  simplified, bolts as single marks. Light enough to inline.

**What Pierre picked** (2026-09-02): `hand-logo-e2-favicon-cleaned.svg` for
the sidebar and header, `favicon/g7-detail-full.svg` for the tab icon. He
turned down the two deeper reductions below, the skeleton and the centre
line mark: they save a lot of bytes but drop too much of the drawing to be
worth it. They stay in the tools because they are what proved where the
size floor is.

Rerunning `hand2logo.py` does not reproduce those and does not overwrite them
either, the names differ. The intermediate outputs it does write were deleted
once the cleaned pair existed.

How far down the drawing goes, measured on real renders:

| what | file | works from |
|---|---|---|
| the drawing, flat weights | 218 kB | about 96 px |
| the drawing, two weights (`reweight.py`) | 227 kB | about 48 px |
| the skeleton (`--only-heavy`) | 22 kB | about 32 px |
| members as centre lines (`centerlines.py`) | 1 kB | about 20 px |
| a purpose drawn glyph | 1 kB | 16 px |

So a heavier line hierarchy buys two steps down and the centre line
reduction buys another, but nothing mechanical reaches 16 px: at that size
the members are thinner than a pixel and the drawing greys out. Four
reductions were tried and all four fail there (raising the length threshold
erodes members instead of simplifying them, and fattening the strokes turns
the shape into letters). The 16 px slot of the .ico therefore takes a plain
glyph, which is what `favicon_build.sh` takes a second argument for.

- `tools/reweight.py` gives the cleaned drawing a two weight line
  hierarchy: the long lines of the width 5 layer are promoted to a heavier
  stroke, everything shorter keeps its weight, so bolts, weld marks, small
  clips and short plate edges stay fine. `--heavy` sets the fat width,
  `--min-len` how long a line must be to earn it (in plot units, the
  cleaned E2 drawing is 2446 wide). A short line whose two ends both land
  on the end of a promoted line is promoted too, otherwise every beam necks
  in at its tip.

  `--from-width` says which layer to promote, 5 by default. The plates that
  `cad2logo.py` writes are 7, and the isometric sits in a space about 2.9x
  bigger than E2, so its lengths and widths scale with it. `--only-heavy`
  throws away everything not promoted, leaving the skeleton.

  It splits multi subpath paths first, because `cad2logo.py` writes a whole
  plate as one path with thousands of M segments in it and there is nothing
  to weigh per line until they are separate. Files that are already one path
  per line come through untouched. Running it twice is safe: the promoted
  lines are no longer at `--from-width`, so a second pass skips them, and it
  refuses to write an empty file rather than silently blanking the drawing.

  Why bother: flat line work fades to an even grey when you shrink it. With
  the hierarchy the members still carry the shape at 96 px and the detail
  appears as the drawing grows.

- `tools/centerlines.py` collapses each member's two flange lines into a
  single line down the middle, so a beam becomes a stroke instead of an
  outline. Feed it the skeleton, not the full drawing. Out of 445 skeleton
  lines it gives about 23 members, under 1 kB, and that is the most reduced
  form of the drawing that is still the drawing. `--grid24` maps it onto the
  same 24 unit box the hand drawn glyphs use and `--color` sets the ink,
  which is how `favicon/g9-drawing.svg` is made. Pierre did not pick it, see
  above; it is kept because it is what fixed where the size floor really is.

- `tools/favicon_sheet.sh` renders every favicon candidate at 16, 32, 48
  and 64 px on white and on dark, blows the pixels up with a point filter
  and writes `favicon/sheet.png`. This is how the marks are judged: a
  smooth preview lies about what a tab draws.
- `tools/favicon_build.sh <glyph>` writes `favicon/build/` from the chosen
  glyph: favicon.svg, favicon.ico (16 + 32 + 48) and apple-touch-icon.png.

The glyphs in `favicon/` are drawn on the same 24 unit grid and in the same
red as the current `frontend/public/favicon.svg`, with the members taken off
the E2 elevation. Eight candidates, from plain to dense: `g1-silhouette`,
`g2-joint`, `g3-cross`, `g4-frame` (5 to 6 strokes each), then
`g5-detail` (11 strokes), `g6-detail-max` (17) and `g7-detail-full` (27
strokes and 4 bolts, the one Pierre picked), which keep the real
member set: the triangulated truss top left with its post and two web
diagonals, the floor beam through the column, the deep girder with its
web splice plates and bolts, the knee brace under the top beam, the brace
into the column base, the base plate. The dense pair uses finer strokes
(1.6 down to 0.65) the way the current iso favicon does, since detail at
32 px and up needs many light lines, not few heavy ones.

`g9-drawing.svg` is the odd one out: not drawn by hand but produced by
`centerlines.py --grid24` from the drawing itself. It beats the hand drawn
glyphs between 20 and 32 px and is under 1 kB, but it was not picked.

All the `g*.svg` are original work (g9 is a reduction of an AISC drawing, so
treat it as derived), which is why they are committed while nothing else in
this folder is.

Two traps the sheet caught: lines closer than about 6 grid units smear
into one band at 16 px, and shapes that close up read as letters (an
early dense draft read as "BF" until the truss got its real bottom chord
and diagonals, and two bolt squares side by side read as a face).

## Rebuilding a view

The intermediate plates are not kept, they are a step on the way to the hand
trimmed file. To get one back, the fabrication package is at
`/mnt/data/Downloads/aisc-steel-sculpture-plans.zip` (12 MB, from the AISC
page in `reference/SOURCES.md`). Extract just the sheet you need, then run
the pipeline **from the repo root**, since `PLT_DIR` in `cad2logo.py` is a
relative path:

```sh
unzip -o "$ZIP" "Steel Sculpture Plans/Drawings - Plot Files/ISO.plt" \
  -d aisc-steel-sculpture-plans/
D=docs/design/aisc-logo
python3 $D/tools/plt2svg.py \
  "aisc-steel-sculpture-plans/Steel Sculpture Plans/Drawings - Plot Files/ISO.plt" \
  $D/raw-iso.svg
python3 $D/tools/cad2logo.py iso $D/plate-iso.svg
python3 $D/tools/cad2full.py iso $D/full-iso.svg
python3 $D/tools/reweight.py $D/plate-iso.svg $D/iso-weighted.svg \
  --from-width 7 --heavy 14 --min-len 147
```

That is how the isometric came back on 2026-09-02 after it was deleted in a
cleanup. The extracted package is gitignored at the repo root.

What cannot be rebuilt is `hand-editted-iso.svg`, the hand trim of the
isometric: it was deleted and it was manual work, so the iso now exists only
as the automatic plates. `hand-editted-e2.svg` is the only copy of the E2
trim, do not delete it.

The weighting carries over to the iso and buys the same two steps down,
readable from about 48 px instead of 96. `--only-heavy` does not: the
isometric's faceted members fall apart into loose rectangles.

Bolt detection in `hand2logo.py` works by ink density: a bolt is a lot of
short strokes packed in a small area, so short segments are clustered by
midpoint proximity and the small, thick, dense blobs are bolts. The
detection is only used for the favicon (a bolt becomes a dot), the
faithful output keeps every stroke. A bolt the detector misses can be
marked by hand: colour its strokes (any non black stroke) in a copy of
the faithful output named `hand-marks-<view>.svg` and rerun the tool.
