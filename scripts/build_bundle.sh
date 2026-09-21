#!/usr/bin/env bash
# Build dist/mdconvert.zip: the skill folder, ready to upload.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAGE="$(mktemp -d)"
DEST="$ROOT/dist"

mkdir -p "$STAGE/mdconvert/scripts" "$STAGE/mdconvert/docs" "$DEST"
cp "$ROOT/SKILL.md"                      "$STAGE/mdconvert/"
cp "$ROOT/scripts/mdconvert_extract.py"  "$STAGE/mdconvert/scripts/"
cp "$ROOT/requirements.txt"              "$STAGE/mdconvert/"
cp "$ROOT/LICENSE"                       "$STAGE/mdconvert/"
cp "$ROOT"/docs/*.md                     "$STAGE/mdconvert/docs/"

rm -f "$DEST/mdconvert.zip"
( cd "$STAGE" && zip -qr "$DEST/mdconvert.zip" mdconvert )
rm -rf "$STAGE"

echo "wrote $DEST/mdconvert.zip"
unzip -l "$DEST/mdconvert.zip"
