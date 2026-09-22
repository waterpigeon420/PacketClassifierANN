"""Diff per-packet classification results between the C++ and Python pipelines.

Reads two CSVs, each produced independently:
    network-packet-classification's `-o <path>` flag
        -> packet_index,matched_priority
    pipeline/run_pipeline.py's `--out <path>` flag
        -> packet_index,matched_priority,generating_filter_index

and reports whether they agree on matched_priority per packet (extra columns,
like generating_filter_index, are ignored).

Usage:
    python compare_results.py <cpp_csv> <py_csv>
"""

import csv
import sys


def load(path: str) -> dict[int, int]:
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        return {int(row["packet_index"]): int(row["matched_priority"]) for row in reader}


def main():
    if len(sys.argv) != 3:
        print("usage: compare_results.py <cpp_csv> <py_csv>", file=sys.stderr)
        sys.exit(2)
    cpp_path, py_path = sys.argv[1], sys.argv[2]

    cpp = load(cpp_path)
    py = load(py_path)

    if cpp.keys() != py.keys():
        print(
            f"MISMATCH: different packet counts ({len(cpp)} cpp vs {len(py)} python)"
        )
        sys.exit(1)

    n = len(cpp)
    mismatches = [i for i in cpp if cpp[i] != py[i]]
    if mismatches:
        print(
            f"MISMATCH: cpp vs python disagree on {len(mismatches)}/{n} packets, "
            f"e.g. indices {mismatches[:10]}"
        )
        for i in mismatches[:10]:
            print(f"  packet {i}: cpp={cpp[i]} python={py[i]}")
        sys.exit(1)

    print(f"OK: cpp and python agree on all {n} packets.")


if __name__ == "__main__":
    main()
