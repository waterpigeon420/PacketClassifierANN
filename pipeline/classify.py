"""Classifiers that match packets against a ClassBench-ng ruleset.

Both implementations return the same thing: for each packet, the priority
(0-indexed rule line number) of the first rule in priority order that
matches it, or -1 if none match. `linear_search` is the simple reference
loop; `linear_search_numpy` is a vectorized rule-major sweep for iterating
quickly over larger rule/packet sets.
"""

from classbench_io import Packet, Rule


def linear_search(rules: list[Rule], packets: list[Packet]) -> list[int]:
    results = []
    for pkt in packets:
        match = -1
        for rule in rules:
            if rule.matches(pkt):
                match = rule.priority
                break
        results.append(match)
    return results


def linear_search_numpy(rules: list[Rule], packets: list[Packet]):
    """Rule-major vectorized sweep: for each rule (in priority order),
    numpy-compare it against every still-unmatched packet at once. Runs in
    O(num_rules) Python-level iterations instead of O(num_rules * num_packets).
    """
    import numpy as np

    n = len(packets)
    src = np.fromiter((p.src for p in packets), dtype=np.uint32, count=n)
    dst = np.fromiter((p.dst for p in packets), dtype=np.uint32, count=n)
    sport = np.fromiter((p.sport for p in packets), dtype=np.uint32, count=n)
    dport = np.fromiter((p.dport for p in packets), dtype=np.uint32, count=n)
    proto = np.fromiter((p.proto for p in packets), dtype=np.uint32, count=n)

    matched = np.full(n, -1, dtype=np.int64)
    unresolved = np.ones(n, dtype=bool)

    for rule in rules:
        if not unresolved.any():
            break
        idx = np.flatnonzero(unresolved)
        mask = (
            (src[idx] >= rule.src_lo)
            & (src[idx] <= rule.src_hi)
            & (dst[idx] >= rule.dst_lo)
            & (dst[idx] <= rule.dst_hi)
            & (sport[idx] >= rule.sport_lo)
            & (sport[idx] <= rule.sport_hi)
            & (dport[idx] >= rule.dport_lo)
            & (dport[idx] <= rule.dport_hi)
        )
        if rule.proto_mask != 0:
            mask &= (proto[idx] & rule.proto_mask) == (
                rule.proto_val & rule.proto_mask
            )
        hit = idx[mask]
        matched[hit] = rule.priority
        unresolved[hit] = False

    return matched.tolist()
