#!/usr/bin/env python3
"""Convert a PRIVATE MAME MPC2000XL port tap log to ordered raw commands.

This does not fabricate descriptor values, infer timings, or modify PCM.
A 48-byte block captured from ES:BX is only a CANDIDATE until the guest
made a valid program/note and playback is independently demonstrated.

Usage:
  python scripts/mpc2000xl_host_trace.py error.log --out private/host.jsonl
"""
import argparse
import json
import re
from pathlib import Path

HOST = re.compile(
    r"MPCXL_HOST seq=(\d+) tick=(-?\d+) dir=(write|read) "
    r"port=([0-9a-fA-F]{4}) data=([0-9a-fA-F]{4}) "
    r"mask=([0-9a-fA-F]{4}) pc=([0-9a-fA-F]{8})"
    r"(?: es=([0-9a-fA-F]{4}) bx=([0-9a-fA-F]{4}))?"
)
DESCRIPTOR = re.compile(
    r"MPCXL_DESCRIPTOR_CANDIDATE tick=(-?\d+) pc=([0-9a-fA-F]{8}) "
    r"es=([0-9a-fA-F]{4}) bx=([0-9a-fA-F]{4}) "
    r"physical_candidate=([0-9a-fA-F]{8}) bytes=([0-9a-fA-F]+)"
)

def parse(source: Path) -> tuple[list[dict], list[dict]]:
    events, candidates = [], []
    last_seq = -1
    for line_number, line in enumerate(source.read_text(errors="replace").splitlines(), 1):
        h = HOST.search(line)
        if h:
            seq, tick, direction, port, raw, mask, pc, es, bx = h.groups()
            seq = int(seq)
            if seq <= last_seq:
                raise ValueError(f"non-monotonic host sequence at line {line_number}")
            last_seq = seq
            entry = {
                "sequence": seq,
                "chip_tick": int(tick),
                "direction": direction,
                "port": int(port, 16),
                "data": int(raw, 16),
                "mask": int(mask, 16),
                "cpu_pc": int(pc, 16),
                "source_line": line_number,
            }
            if es is not None:
                entry["es"] = int(es, 16)
                entry["bx"] = int(bx, 16)
            events.append(entry)
        d = DESCRIPTOR.search(line)
        if d:
            tick, pc, es, bx, physical, hexdump = d.groups()
            payload = bytes.fromhex(hexdump)
            if len(payload) != 48:
                raise ValueError(f"descriptor at line {line_number} has {len(payload)} bytes, not 48")
            candidates.append({
                "chip_tick": int(tick),
                "cpu_pc": int(pc, 16),
                "es": int(es, 16),
                "bx": int(bx, 16),
                "physical_candidate": int(physical, 16),
                "bytes_hex": payload.hex(),
                "source_line": line_number,
                "verification": "candidate_only_not_proven_note_descriptor",
            })
    return events, candidates

def main() -> None:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("log", type=Path)
    cli.add_argument("--out", required=True, type=Path)
    cli.add_argument("--require-host-writes", action="store_true",
                     help="Fail if native CPU did not access sound chip")
    args = cli.parse_args()
    events, candidates = parse(args.log)
    if args.require_host_writes and not any(x["direction"] == "write" for x in events):
        cli.error("no native L6028 writes observed")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as out:
        for item in events:
            out.write(json.dumps(item, separators=(",", ":")) + "\n")
    candidates_file = args.out.with_suffix(".descriptors.json")
    candidates_file.write_text(json.dumps(candidates, indent=2) + "\n", encoding="utf-8")
    keyon_candidates = [
        x for x in events if x["direction"] == "write" and
        x["port"] in (0x88, 0x89) and (x["mask"] & 0xff00) and (x["data"] & 0x0100)
    ]
    print(json.dumps({
        "raw_host_operations": len(events),
        "writes": sum(x["direction"] == "write" for x in events),
        "descriptor_candidates": len(candidates),
        "keyon_port_write_candidates": len(keyon_candidates),
        "note_and_nonzero_audio_proven": False,
        "output": str(args.out),
        "descriptor_metadata": str(candidates_file),
    }, indent=2))

if __name__ == "__main__":
    main()
