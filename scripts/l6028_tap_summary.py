#!/usr/bin/env python3
"""Summarize L6028_TAP records emitted by a trace-enabled MAME L6028 build.

Usage: python scripts/l6028_tap_summary.py error.log
This utility does not modify or resample PCM. It is a streaming trace counter.
"""
from __future__ import annotations
import argparse
from collections import Counter
from pathlib import Path

MARKER = "L6028_TAP "

def load_events(path: Path) -> list[tuple[str, dict[str, str]]]:
    """Load a *small* deterministic fixture as (kind, properties) for tests."""
    events: list[tuple[str, dict[str, str]]] = []
    with path.open("r", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            ix = line.find(MARKER)
            if ix < 0:
                continue
            tokens = line[ix + len(MARKER):].split()
            if not tokens:
                continue
            events.append((tokens[0], dict(s.split("=", 1) for s in tokens[1:] if "=" in s)))
    return events

def summarize(path: Path) -> None:
    kinds: Counter[str] = Counter()
    voices: Counter[str] = Counter()
    first_frame: int | None = None
    last_frame: int | None = None
    bad_records = 0
    with path.open("r", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            ix = line.find(MARKER)
            if ix < 0:
                continue
            fields = line[ix + len(MARKER):].split()
            if not fields:
                bad_records += 1
                continue
            kinds[fields[0]] += 1
            values = dict(token.split("=", 1) for token in fields[1:] if "=" in token)
            if "voice" in values:
                voices[values["voice"]] += 1
            if "frame" in values:
                try:
                    frame = int(values["frame"])
                except ValueError:
                    bad_records += 1
                    continue
                first_frame = frame if first_frame is None else min(first_frame, frame)
                last_frame = frame if last_frame is None else max(last_frame, frame)
    print(f"Trace file: {path}")
    print(f"Frame span: {first_frame}..{last_frame}")
    print(f"Malformed trace lines: {bad_records}")
    print("Events:")
    for name, count in sorted(kinds.items()):
        print(f"  {name}: {count}")
    print(f"Voices observed: {', '.join(sorted(voices, key=int)) or '(none)'}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("logfile", type=Path)
    args = ap.parse_args()
    summarize(args.logfile)
