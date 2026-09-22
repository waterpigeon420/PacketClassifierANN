#!/usr/bin/env bash
# Classify a generated dataset with the Python pipeline (fast iteration,
# no C++ rebuild). Thin wrapper around pipeline/run_pipeline.py using the
# data/<name>/ convention -- for other options (--limit, --out) call
# pipeline/run_pipeline.py directly.
#
# Usage: classify_py.sh <name> [engine] [extra run_pipeline.py args, e.g. --limit 500]
#
#   name    subfolder under data/ to classify (as produced by generate.sh).
#   engine  python (plain-loop reference) or numpy (vectorized, default).
#           Only consumed if it's a bare word right after <name>; anything
#           starting with "-" is treated as an extra run_pipeline.py arg.
set -euo pipefail

NAME=${1:?"usage: classify_py.sh <name> [engine] [extra args]"}
shift
ENGINE=numpy
if [ $# -gt 0 ] && [[ "$1" != -* ]]; then
  ENGINE=$1
  shift
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="$ROOT/data/$NAME"

if [ ! -f "$DATA_DIR/ruleset.txt" ] || [ ! -f "$DATA_DIR/trace.txt" ]; then
  echo "error: $DATA_DIR/ruleset.txt or trace.txt not found -- run scripts/generate.sh first" >&2
  exit 1
fi

python3 "$ROOT/pipeline/run_pipeline.py" \
  --rules "$DATA_DIR/ruleset.txt" \
  --trace "$DATA_DIR/trace.txt" \
  --engine "$ENGINE" \
  "$@"
