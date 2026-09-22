# Python classification pipeline

Classifies the ruleset + trace files produced by ClassBench-ng
(`../classbench-packet-classification`) without needing to rebuild the C++
tool in `../network-packet-classification`. For iterating on classifier
logic quickly; not a replacement for the C++ classifiers.

## Usage

Via the top-level `data/<name>/` convention (see the repo root README) --
this is the normal path:

```
docker compose run --rm dev scripts/classify_py.sh <name>
docker compose run --rm dev scripts/classify_py.sh <name> python   # plain-loop engine
docker compose run --rm dev scripts/classify_py.sh <name> --limit 1000
docker compose run --rm dev scripts/classify_py.sh <name> --out results.csv
```

Or run directly against arbitrary files:

```
pip install -r requirements.txt   # numpy, for the vectorized engine

python run_pipeline.py --rules <ruleset_file> --trace <trace_file>
python run_pipeline.py --rules <ruleset_file> --trace <trace_file> --engine python
python run_pipeline.py --rules <ruleset_file> --trace <trace_file> --limit 1000
python run_pipeline.py --rules <ruleset_file> --trace <trace_file> --out results.csv
```

To check the Python pipeline's results against the C++ classifier's, see
"Compare C++ vs Python results" in the repo root README.

## Files

- `classbench_io.py` -- parses ruleset lines (`@src/plen  dst/plen  sport:sport  dport:dport  proto/mask  flags/mask`)
  and trace lines (`src  dst  sport  dport  proto  flags  filter_index`).
- `classify.py` -- `linear_search` (plain Python, the reference implementation)
  and `linear_search_numpy` (vectorized, ~2-3x faster on rule sets up to a
  few thousand rules).
- `run_pipeline.py` -- CLI wrapping the above.
- `compare_results.py` -- diffs a `--out` CSV from this pipeline against a
  `-o` CSV from the C++ classifier (see repo root README).

## Notes

- Priority = line number in the ruleset file (0-indexed), first line wins ties.
- The "agrees with generating rule" stat compares the match against the
  trace's embedded ground-truth filter index. It's informational, not a
  correctness check -- ClassBench rulesets have legitimate overlapping
  rules, so a packet can be classified by a higher-priority rule than the
  one it was originally sampled from. Expect high-90s%, not 100%.
- `linear_search_numpy` is rule-major (loops over rules, vectorizes across
  packets), so its cost scales with rule count. It's much faster than the
  plain-Python engine up to a few thousand rules, but at ~100k rules the
  per-rule Python loop overhead dominates and throughput drops to ~2k
  packets/sec -- fine for iterating on moderate ACL/firewall-sized rule
  sets (the classbench-ng default profiles), not a substitute for the C++
  classifiers at ClassBench's 100k-rule scale.
