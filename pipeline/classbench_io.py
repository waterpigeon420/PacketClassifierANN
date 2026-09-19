"""Parsers for ClassBench-ng ruleset and trace_generator trace files.

Ruleset line (IPv4 5-tuple, one rule per line, in priority order --
first line = highest priority):

    @<src_ip>/<plen>\t<dst_ip>/<plen>\t<sport_lo> : <sport_hi>\t<dport_lo> : <dport_hi>\t<proto>/<mask>\t<flags>/<mask>

Trace line (one packet per line, produced by trace_generator):

    <src_ip_int>\t<dst_ip_int>\t<sport>\t<dport>\t<proto>\t<flags>\t<filter_index>

`filter_index` is the 0-indexed line number of the rule that generated the
packet. It is ground truth for "which rule was this packet drawn from", not
necessarily the first-matching rule under priority order (multiple rules can
overlap a packet), so use it to sanity-check a classifier, not as the sole
correctness oracle.
"""

import ipaddress
from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    priority: int  # 0-indexed line number; lower = higher priority
    src_lo: int
    src_hi: int
    dst_lo: int
    dst_hi: int
    sport_lo: int
    sport_hi: int
    dport_lo: int
    dport_hi: int
    proto_val: int
    proto_mask: int

    def matches(self, pkt) -> bool:
        if not (self.src_lo <= pkt.src <= self.src_hi):
            return False
        if not (self.dst_lo <= pkt.dst <= self.dst_hi):
            return False
        if not (self.sport_lo <= pkt.sport <= self.sport_hi):
            return False
        if not (self.dport_lo <= pkt.dport <= self.dport_hi):
            return False
        if self.proto_mask != 0 and (pkt.proto & self.proto_mask) != (
            self.proto_val & self.proto_mask
        ):
            return False
        return True


@dataclass(frozen=True)
class Packet:
    src: int
    dst: int
    sport: int
    dport: int
    proto: int
    filter_index: int  # ground-truth generating rule (0-indexed), or -1


def _parse_cidr(field: str) -> tuple[int, int]:
    ip, plen = field.split("/")
    net = ipaddress.ip_network(f"{ip}/{plen}", strict=False)
    return int(net.network_address), int(net.broadcast_address)


def parse_ruleset(path: str) -> list[Rule]:
    rules: list[Rule] = []
    with open(path) as f:
        for priority, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            src, dst, sport, dport, proto, *_rest = line.split("\t")
            src_lo, src_hi = _parse_cidr(src.lstrip("@"))
            dst_lo, dst_hi = _parse_cidr(dst)
            sport_lo, sport_hi = (int(x) for x in sport.split(":"))
            dport_lo, dport_hi = (int(x) for x in dport.split(":"))
            proto_val_s, proto_mask_s = proto.split("/")
            rules.append(
                Rule(
                    priority=priority,
                    src_lo=src_lo,
                    src_hi=src_hi,
                    dst_lo=dst_lo,
                    dst_hi=dst_hi,
                    sport_lo=sport_lo,
                    sport_hi=sport_hi,
                    dport_lo=dport_lo,
                    dport_hi=dport_hi,
                    proto_val=int(proto_val_s, 16),
                    proto_mask=int(proto_mask_s, 16),
                )
            )
    return rules


def parse_trace(path: str) -> list[Packet]:
    packets: list[Packet] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            cols = line.split("\t")
            src, dst, sport, dport, proto = cols[:5]
            filter_index = int(cols[6]) if len(cols) > 6 else -1
            packets.append(
                Packet(
                    src=int(src),
                    dst=int(dst),
                    sport=int(sport),
                    dport=int(dport),
                    proto=int(proto),
                    filter_index=filter_index,
                )
            )
    return packets
