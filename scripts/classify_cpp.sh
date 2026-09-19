#!/usr/bin/env bash
# Build (if needed) and run the C++ classifier against a generated dataset.
#
# Usage: classify_cpp.sh <name> [classifier]
#
#   name        subfolder under data/ to classify (as produced by generate.sh).
#                Reads data/<name>/ruleset.txt and data/<name>/trace.txt.
#   classifier  name registered in main.cpp's classifier dispatch (default:
#                linear). Currently only "linear" (LinearSearch, brute-force
#                first-match-in-priority-order) is registered -- KsetSearch
#                and TSearch only implement partition()/build-phase so far.
#                See the top-level README's "Adding your own classifier".
set -euo pipefail

NAME=${1:?"usage: classify_cpp.sh <name> [classifier]"}
CLASSIFIER=${2:-linear}

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NPC_DIR="$ROOT/network-packet-classification"
DATA_DIR="$ROOT/data/$NAME"
BUILD_DIR="$NPC_DIR/build/Debug"

if [ ! -f "$DATA_DIR/ruleset.txt" ] || [ ! -f "$DATA_DIR/trace.txt" ]; then
  echo "error: $DATA_DIR/ruleset.txt or trace.txt not found -- run scripts/generate.sh first" >&2
  exit 1
fi

if [ ! -d "$NPC_DIR/classifiers" ]; then
  echo "error: network-packet-classification isn't on a branch with classifiers/" >&2
  echo "  run: git -C network-packet-classification checkout rule5D" >&2
  exit 1
fi

mkdir -p "$BUILD_DIR"
[ -f "$BUILD_DIR/Makefile" ] || (cd "$BUILD_DIR" && cmake ../../ >/dev/null)
(cd "$BUILD_DIR" && make --quiet)

"$BUILD_DIR/m" -r "$DATA_DIR/ruleset.txt" -p "$DATA_DIR/trace.txt" -c "$CLASSIFIER"
