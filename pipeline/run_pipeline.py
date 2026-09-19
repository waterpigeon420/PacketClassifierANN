"""CLI: classify a ClassBench-ng ruleset + trace_generator trace in Python.

Meant for fast iteration on classifier logic without a C++ rebuild -- point
it at the ruleset/trace files produced by classbench-ng and trace_generator
(see ../classbench-packet-classification) and get match results + timing in
seconds.

Examples:
    python run_pipeline.py --rules acl1_1000.txt --trace acl1_1000.txt_trace
    python run_pipeline.py --rules acl1_1000.txt --trace acl1_1000.txt_trace \\
        --engine python --limit 500 --out results.csv
    python run_pipeline.py --rules acl1_1000.txt --trace acl1_1000.txt_trace \\
        --compare
"""

import argparse
import csv
import sys
import time

from classbench_io import parse_ruleset, parse_trace
from classify import linear_search, linear_search_numpy

ENGINES = {
    "python": linear_search,
    "numpy": linear_search_numpy,
}


def run(engine_name: str, rules, packets):
    engine = ENGINES[engine_name]
    start = time.perf_counter()
    results = engine(rules, packets)
    elapsed = time.perf_counter() - start
    return results, elapsed


def summarize(results, packets, elapsed, label):
    n = len(packets)
    matched = sum(1 for r in results if r != -1)
    agree = sum(
        1
        for r, p in zip(results, packets)
        if p.filter_index != -1 and r == p.filter_index
    )
    print(f"--- {label} ---")
    print(f"packets: {n}")
    print(f"matched: {matched} ({matched / n:.2%})")
    print(f"unmatched: {n - matched}")
    print(
        f"agrees with generating rule (informational, overlaps make <100% "
        f"expected): {agree}/{n} ({agree / n:.2%})"
    )
    print(f"elapsed: {elapsed:.4f}s  ({n / elapsed:,.0f} packets/sec)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rules", required=True, help="path to ClassBench-ng ruleset file")
    ap.add_argument("--trace", required=True, help="path to trace_generator trace file")
    ap.add_argument("--engine", choices=ENGINES, default="numpy")
    ap.add_argument("--limit", type=int, default=None, help="only classify the first N packets")
    ap.add_argument("--out", help="write per-packet results to this CSV path")
    ap.add_argument(
        "--compare",
        action="store_true",
        help="run both engines and report whether their outputs match",
    )
    args = ap.parse_args()

    print(f"Loading ruleset: {args.rules}")
    rules = parse_ruleset(args.rules)
    print(f"Loading trace: {args.trace}")
    packets = parse_trace(args.trace)
    if args.limit:
        packets = packets[: args.limit]
    print(f"{len(rules)} rules, {len(packets)} packets\n")

    if args.compare:
        results_by_engine = {}
        for name in ENGINES:
            results, elapsed = run(name, rules, packets)
            results_by_engine[name] = results
            summarize(results, packets, elapsed, name)
            print()
        names = list(results_by_engine)
        baseline = results_by_engine[names[0]]
        for name in names[1:]:
            mismatches = [
                i
                for i, (a, b) in enumerate(zip(baseline, results_by_engine[name]))
                if a != b
            ]
            if mismatches:
                print(
                    f"MISMATCH: {names[0]} vs {name} disagree on "
                    f"{len(mismatches)} packets, e.g. indices {mismatches[:10]}"
                )
                sys.exit(1)
        print(f"OK: all engines ({', '.join(names)}) agree.")
        results = baseline
    else:
        results, elapsed = run(args.engine, rules, packets)
        summarize(results, packets, elapsed, args.engine)

    if args.out:
        with open(args.out, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["packet_index", "matched_priority", "generating_filter_index"])
            for i, (r, p) in enumerate(zip(results, packets)):
                writer.writerow([i, r, p.filter_index])
        print(f"\nWrote per-packet results to {args.out}")


if __name__ == "__main__":
    main()
