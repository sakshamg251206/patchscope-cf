#!/bin/sh
# Build the public release archive from exactly what git tracks, so the zip can never
# contain an ignored cache, a virtualenv or an untracked stray file.
set -eu
out="${1:-release/patchscope-cf.zip}"
mkdir -p "$(dirname "$out")"
rm -f "$out"
git archive --format=zip --prefix=patchscope-cf/ -o "$out" HEAD
echo "wrote $out"
unzip -l "$out" | tail -1
