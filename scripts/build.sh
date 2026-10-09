#!/usr/bin/env bash
# Build Mayhem with the Meshtastic app from upstream PR #3306 plus the patches in ../patches (Docker required).
# Usage: scripts/build.sh            -> dist/mesh-pr3306-aes256/{FIRMWARE,APPS,BASEBAND}
set -euo pipefail
PR=3306
PR_COMMIT=51135ec96d7c3625edfa6bd879d2d2bc2850594c   # head of the PR this repository was built and tested against
VER=mesh-pr3306-aes256                                  # version string: the ppma compatibility hash is derived from it
HERE="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$HERE/build/mayhem"
OUT="$HERE/dist/$VER"

mkdir -p "$HERE/build" "$OUT"
if [ ! -d "$WORK/.git" ]; then
  git clone --no-checkout https://github.com/portapack-mayhem/mayhem-firmware.git "$WORK"
fi
git -C "$WORK" fetch --depth 1 origin "pull/$PR/head"
HEAD_SHA="$(git -C "$WORK" rev-parse FETCH_HEAD)"
if [ "$HEAD_SHA" != "$PR_COMMIT" ]; then
  echo "PR #$PR head is now $HEAD_SHA, this repository was tested with $PR_COMMIT."
  echo "Fetching the pinned commit instead (may fail if the PR branch was force-pushed)."
  git -C "$WORK" fetch --depth 1 origin "$PR_COMMIT"
fi
git -C "$WORK" checkout -q --force "$PR_COMMIT"
git -C "$WORK" clean -fdq -e build
git -C "$WORK" submodule update --init --recursive --depth 1
for p in "$HERE"/patches/*.patch; do git -C "$WORK" apply "$p"; done

docker image inspect portapack-dev >/dev/null 2>&1 || docker build -t portapack-dev -f "$WORK/dockerfile-nogit" "$WORK"
mkdir -p "$WORK/build"
# parallel make occasionally races on libopencm3 on the first run; a retry resumes where it stopped
for i in 1 2 3; do docker run --rm -e VERSION_STRING="$VER" -v "$WORK":/havoc portapack-dev -j4 && break; done

B="$WORK/build/firmware"
rm -rf "$OUT"; mkdir -p "$OUT/FIRMWARE"
cp "$B/portapack-mayhem-firmware.bin" "$OUT/FIRMWARE/portapack-mayhem_mesh-aes256.bin"
cp -R "$B/firmware_tar/APPS" "$OUT/APPS"
cp -R "$B/firmware_tar/BASEBAND" "$OUT/BASEBAND"
echo "built: $OUT  (copy FIRMWARE, APPS and BASEBAND to the SD card, then flash the .bin with Flash Utility)"
