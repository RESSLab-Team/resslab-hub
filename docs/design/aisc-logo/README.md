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
- `tools/hand2logo.py` reads the hand-trimmed drawings and builds the
  outputs: faithful (centerline strokes, width 5, hardware at width 2,
  all the detail kept, this is the logo) and favicon (collinear fragments
  joined, close parallel pairs merged, small hardware dropped, every bolt
  replaced by one simple mark: a circle when the symbol is about round, a
  rectangle when it is long). The favicon comes in two styles, outline
  and filled, to compare. Default view is e2, the 2D one dlignos picked
  in #263 (pass `iso` to rebuild the isometric).

Bolt detection in `hand2logo.py` works by ink density: a bolt is a lot of
short strokes packed in a small area, so short segments are clustered by
midpoint proximity and the small, thick, dense blobs are bolts. The
detection is only used for the favicon (a bolt becomes a dot), the
faithful output keeps every stroke. A bolt the detector misses can be
marked by hand: colour its strokes (any non black stroke) in a copy of
the faithful output named `hand-marks-<view>.svg` and rerun the tool.
