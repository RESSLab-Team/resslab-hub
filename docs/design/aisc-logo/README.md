# AISC steel sculpture logo tools

Scripts that turn the AISC steel sculpture shop drawings into logo
candidates for the hub (issue #263). Only the scripts are committed: the
drawings and every SVG derived from them are AISC copyright, so they stay
out of git (see `.gitignore`) and live only on local machines.

Pipeline, in order:

- `tools/plt2svg.py` decodes an HPGL2 `.plt` pen plot (the only true
  vector export in the official plans package) into a full sheet SVG.
- `tools/cad2logo.py` builds clean one-ink plates per view: filled pen
  quads collapsed back to centerline strokes, dimensions, text and
  callouts dropped, bolts as solid dots.
- `tools/cad2full.py` builds full plates (everything except text) as
  layered Inkscape files, for manual cleaning.
- `tools/hand2logo.py` reads the hand-trimmed drawings and builds three
  logo candidates per view: faithful (centerline strokes, width 5,
  hardware at width 2), simplified (collinear fragments joined, close
  parallel pairs merged, bolts replaced by shared `<defs>` glyphs stamped
  with `<use>`), and two tone (same, bolts in EPFL red #e30713).

Bolt detection in `hand2logo.py` works by ink density: a bolt is a lot of
short strokes packed in a small area, so short segments are clustered by
midpoint proximity and the small, thick, dense blobs are bolts. Identical
bolts share one glyph and the whole `<g id="bolts">` recolours in one
edit. A bolt the detector misses can be marked by hand: colour its strokes
(any non black stroke) in a copy of the faithful output named
`hand-marks-<view>.svg` and rerun the tool.
