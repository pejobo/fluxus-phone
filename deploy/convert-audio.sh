#!/bin/bash
# Convert m4a files from ORIGINAL/ to 8kHz mono WAV in the stick root.
# provide directory of usb stick as parameter

set -euo pipefail

DIR=$1

if [[ ! -d "$DIR/ORIGINAL" ]]; then
    echo "ERROR: no ORIGINAL/ directory found in $DIR" >&2
    exit 1
fi

for src in "$DIR/ORIGINAL"/*.m4a; do
    [[ -f "$src" ]] || continue
    name=$(basename "$src" .m4a)
    ffmpeg -i "$src" -ar 8000 -ac 1 -sample_fmt s16 -y "$DIR/${name}.wav"
    echo "converted: $DIR/${name}.wav"
done
