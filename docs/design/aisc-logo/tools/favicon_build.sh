#!/usr/bin/env bash
# Build the production favicon files from one chosen glyph.
#
#   bash tools/favicon_build.sh g7-detail-full
#   bash tools/favicon_build.sh g7-detail-full g4-frame
#
# Writes into favicon/build/: favicon.svg, favicon.ico (16 + 32 + 48) and
# apple-touch-icon.png (180). Nothing is copied into frontend/public/ here,
# that happens only once dlignos confirms the mark on #263.
#
# The 16 px slot of the .ico is drawn from a copy with the strokes scaled
# x1.15: at that size a thin line lands on less than one pixel and goes pale
# grey. The same trick was used for the current iso favicon.
#
# A second glyph name is optional. An .ico holds one image per size, so a
# dense mark that only reads from 32 px up can keep a plain one in the 16 px
# slot. The .svg cannot do that (one drawing for every size), but a browser
# on a hidpi screen renders it at 32 device px or more anyway, so the dense
# glyph is the right thing to put there.
set -eu

HERE=$(cd "$(dirname "$0")" && pwd)
BASE=$(dirname "$HERE")
GLYPH=${1:?usage: favicon_build.sh <glyph> [glyph for the 16 px ico slot]}
SRC=$BASE/favicon/$GLYPH.svg
[ -f "$SRC" ] || { echo "no such glyph: $SRC" >&2; exit 1; }

SMALL=${2:-$GLYPH}
SRC16=$BASE/favicon/$SMALL.svg
[ -f "$SRC16" ] || { echo "no such glyph: $SRC16" >&2; exit 1; }

OUT=$BASE/favicon/build
WORK=${TMPDIR:-/tmp}/favicon-build
CONVERT=/usr/bin/convert
rm -rf "$WORK" "$OUT"; mkdir -p "$WORK" "$OUT"

cp "$SRC" "$OUT/favicon.svg"

# boosted copy for the 16 px slot
python3 - "$SRC16" "$WORK/boost.svg" <<'PY'
import re, sys
t = open(sys.argv[1]).read()
t = re.sub(r'stroke-width="([\d.]+)"',
           lambda m: 'stroke-width="%.2f"' % (float(m.group(1)) * 1.15), t)
t = re.sub(r'(<rect [^>]*?)width="([\d.]+)" height="([\d.]+)"',
           lambda m: '%swidth="%.2f" height="%.2f"'
                     % (m.group(1), float(m.group(2)) * 1.15,
                        float(m.group(3)) * 1.15), t)
open(sys.argv[2], "w").write(t)
PY

png() {  # <svg> <px> <out>
  inkscape --export-type=png --export-filename="$3" -w "$2" -h "$2" \
           --export-background-opacity=0 "$1" >/dev/null 2>&1
}
png "$WORK/boost.svg" 16 "$WORK/16.png"
png "$SRC" 32 "$WORK/32.png"
png "$SRC" 48 "$WORK/48.png"
$CONVERT "$WORK/16.png" "$WORK/32.png" "$WORK/48.png" "$OUT/favicon.ico"

# home screen icon: white ground, the glyph inset so it is not cropped by
# the rounded corners iOS puts on it
png "$SRC" 152 "$WORK/180.png"
$CONVERT "$WORK/180.png" -background white -gravity center -extent 180x180 \
         "$OUT/apple-touch-icon.png"

echo "built from $GLYPH (16 px slot: $SMALL):"
$CONVERT "$OUT/favicon.ico" -format "  favicon.ico        %wx%h\n" info:
$CONVERT "$OUT/apple-touch-icon.png" -format "  apple-touch-icon   %wx%h\n" info:
echo "  favicon.svg        $(wc -c < "$OUT/favicon.svg") bytes"
