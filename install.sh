#!/usr/bin/env sh
# CIP installer — drop repository intelligence into any repo.
# Usage: ./install.sh [TARGET_REPO]   (default: current directory)
set -eu
SRC="$(cd "$(dirname "$0")" && pwd)"
TARGET="$(cd "${1:-.}" && pwd)"

mkdir -p "$TARGET/.cip/bin" "$TARGET/.cip/lib" "$TARGET/.cip/bootstrap" "$TARGET/.cip/data"
cp "$SRC/bin/cip"                     "$TARGET/.cip/bin/cip"
cp -R "$SRC/lib/cipkg"                "$TARGET/.cip/lib/"
cp "$SRC/bootstrap/AGENTS.md"         "$TARGET/.cip/bootstrap/AGENTS.md"
cp "$SRC/config.default.toml"         "$TARGET/.cip/config.toml"
cp "$SRC/ontology.json"               "$TARGET/.cip/ontology.json"
chmod +x "$TARGET/.cip/bin/cip"

echo "cip: installed to $TARGET/.cip"
cd "$TARGET" && "$TARGET/.cip/bin/cip" init
echo
echo "Optional: export PATH=\"$TARGET/.cip/bin:\$PATH\""
