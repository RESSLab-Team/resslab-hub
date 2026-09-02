#!/usr/bin/env bash
# Pixel proof for the favicon candidates: render each one at the real sizes
# a browser uses, then blow the pixels up with a point filter so we judge
# what the tab actually shows, not a smooth preview.
#
# Note: use /usr/bin/convert (ImageMagick 6). The `magick` on this machine is
# a FUSE AppImage and it fails inside the sandbox.
#
#   bash tools/favicon_sheet.sh   ->  favicon/sheet.png
set -eu

HERE=$(cd "$(dirname "$0")" && pwd)
BASE=$(dirname "$HERE")
OUT=$BASE/favicon
WORK=${TMPDIR:-/tmp}/favicon-sheet
FRONTEND=$(cd "$BASE/../../.." && pwd)/frontend

rm -rf "$WORK"; mkdir -p "$WORK"

CONVERT=/usr/bin/convert
SIZES="16 32 48 64"
ZOOM_16=8; ZOOM_32=4; ZOOM_48=3; ZOOM_64=2   # every cell ends up 128 px wide

render() {  # <svg> <name> <bg hex> <label suffix>
  local svg=$1 name=$2 bg=$3
  local row=()
  for px in $SIZES; do
    inkscape --export-type=png --export-filename="$WORK/$name-$px.png" \
             -w "$px" -h "$px" -b "$bg" "$svg" >/dev/null 2>&1
    local z; eval "z=\$ZOOM_$px"
    $CONVERT "$WORK/$name-$px.png" -filter point -resize "$((z * 100))%" \
             "$WORK/$name-$px-x.png"
    row+=("$WORK/$name-$px-x.png")
  done
  $CONVERT "${row[@]}" -background '#9a9a9a' -splice 6x0 +append "$WORK/$name-row.png"
}

label() {  # <name> <text>  -> row with a caption strip on the left
  $CONVERT -size 150x128 -background '#9a9a9a' -fill '#111' -pointsize 15 \
           -gravity west "caption:  $2" "$WORK/$1-cap.png"
  $CONVERT "$WORK/$1-cap.png" "$WORK/$1-row.png" +append "$WORK/$1-full.png"
}

rows=()
add() {  # <svg> <name> <label>
  render "$1" "$2-lt" '#ffffff'
  render "$1" "$2-dk" '#1e1e1e'
  $CONVERT "$WORK/$2-lt-row.png" "$WORK/$2-dk-row.png" \
           -background '#9a9a9a' -splice 14x0 +append "$WORK/$2-row.png"
  label "$2" "$3"
  rows+=("$WORK/$2-full.png")
}

for g in "$OUT"/g*.svg; do
  [ -e "$g" ] || continue
  n=$(basename "$g" .svg)
  add "$g" "$n" "$n"
done
[ -e "$BASE/hand-logo-e2-crop.svg" ] && add "$BASE/hand-logo-e2-crop.svg" "crop" "e2 crop"
[ -e "$BASE/hand-logo-e2-favicon-filled.svg" ] && add "$BASE/hand-logo-e2-favicon-filled.svg" "full" "e2 full view"
[ -e "$FRONTEND/public/favicon.svg" ] && add "$FRONTEND/public/favicon.svg" "current" "current (iso)"

# header: the sizes, twice (light then dark)
hdr() { $CONVERT -size 522x22 -background '#9a9a9a' -fill '#111' -pointsize 14 \
        -gravity west "caption:   16 px            32 px            48 px            64 px" "$1"; }
hdr "$WORK/h1.png"; hdr "$WORK/h2.png"
$CONVERT -size 150x22 -background '#9a9a9a' xc:'#9a9a9a' "$WORK/h0.png"
$CONVERT "$WORK/h0.png" "$WORK/h1.png" -background '#9a9a9a' -splice 14x0 \
         "$WORK/h2.png" +append "$WORK/header.png"

mkdir -p "$OUT"
$CONVERT "$WORK/header.png" "${rows[@]}" -background '#9a9a9a' -splice 0x6 -append \
         -bordercolor '#9a9a9a' -border 10 "$OUT/sheet.png"
echo "-> $OUT/sheet.png"
$CONVERT "$OUT/sheet.png" -format "   %wx%h" info:; echo
