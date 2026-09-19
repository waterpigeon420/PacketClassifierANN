#!/usr/bin/env bash
# Generate a ClassBench-ng ruleset + matching packet trace into data/<name>/.
#
# Usage: generate.sh <profile> <rule_count> [name] [pareto_a] [pareto_b] [trace_scale]
#
#   profile      seed profile to generate from (see classbench-packet-classification/
#                parameter_files/): acl1-5 (router ACLs), fw1-5 (firewall
#                rulesets), ipc1-2 (core router "IP chain" classifiers).
#                Each number is a different real-world-derived rule mix, not
#                a size -- acl1 and acl5 are both "ACL-shaped" but come from
#                different sampled routers.
#   rule_count   target number of rules to generate (actual count is usually
#                somewhat lower -- ClassBench-ng drops redundant rules).
#   name         subfolder under data/ to write into (default: <profile>_<rule_count>).
#   pareto_a     trace locality-of-reference shape parameter (default: 1).
#   pareto_b     trace locality-of-reference scale parameter (default: 0.1).
#                a=1,b=0 = no locality; a=1,b=0.0001 = low; a=1,b=1 = high.
#   trace_scale  trace size = rule_count * trace_scale (default: 10).
#
# Output: data/<name>/ruleset.txt, data/<name>/trace.txt
set -euo pipefail

PROFILE=${1:?"usage: generate.sh <profile> <rule_count> [name] [pareto_a] [pareto_b] [trace_scale]"}
COUNT=${2:?"usage: generate.sh <profile> <rule_count> [name] [pareto_a] [pareto_b] [trace_scale]"}
NAME=${3:-${PROFILE}_${COUNT}}
PARETO_A=${4:-1}
PARETO_B=${5:-0.1}
SCALE=${6:-10}

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLASSBENCH_DIR="$ROOT/classbench-packet-classification/classbench-ng"
TRACE_GEN_DIR="$ROOT/classbench-packet-classification/trace_generator"
OUT_DIR="$ROOT/data/$NAME"
mkdir -p "$OUT_DIR"

# One-time (idempotent) toolchain build.
if [ ! -x "$CLASSBENCH_DIR/vendor/db_generator/db_generator" ]; then
  echo "Building ClassBench db_generator (first run only)..."
  # Windows checkouts leave the Ruby scripts with CRLF line endings, which
  # breaks their shebang under Linux/WSL.
  sed -i 's/\r$//' "$CLASSBENCH_DIR/classbench" "$CLASSBENCH_DIR/lib/classbench.rb"
  (cd "$CLASSBENCH_DIR" && make)
fi
if [ ! -x "$TRACE_GEN_DIR/trace_generator" ]; then
  echo "Building trace_generator (first run only)..."
  (cd "$TRACE_GEN_DIR" && make all)
fi

echo "Generating $COUNT-rule '$PROFILE' ruleset -> $OUT_DIR/ruleset.txt"
(
  cd "$CLASSBENCH_DIR"
  ulimit -s 81920
  ./classbench generate v4 "./vendor/parameter_files/${PROFILE}_seed" \
    --count="$COUNT" \
    --db-generator=./vendor/db_generator/db_generator \
    > "$OUT_DIR/ruleset.txt"
)
echo "  -> $(wc -l < "$OUT_DIR/ruleset.txt") rules"

echo "Generating trace (pareto a=$PARETO_A b=$PARETO_B, scale=$SCALE) -> $OUT_DIR/trace.txt"
(
  cd "$TRACE_GEN_DIR"
  ./trace_generator "$PARETO_A" "$PARETO_B" "$SCALE" "$OUT_DIR/ruleset.txt"
)
mv "$OUT_DIR/ruleset.txt_trace" "$OUT_DIR/trace.txt"
echo "  -> $(wc -l < "$OUT_DIR/trace.txt") packets"

echo "Done: $OUT_DIR/ruleset.txt, $OUT_DIR/trace.txt"
