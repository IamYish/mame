#!/usr/bin/env python3
"""Validate MAME L6028 ROM-free fixture log; optional PCM tap checks.

Run:
    py scripts/l6028_fixture_check.py error.log
    py scripts/l6028_fixture_check.py error.log --require-trace

The first form confirms driver event progression only. The second requires
L6028_CAPTURE_TRACE=1, ten channel frames and nonzero main output; not just log
markers. Neither form proves sonic identity with original Akai hardware.
"""
from __future__ import annotations
import argparse
from pathlib import Path

MARKERS = ("L6028_LAB_BEGIN", "L6028_LAB_OVERLAP", "L6028_LAB_DONE")

def verify(path: Path, require_trace: bool = False) -> dict[str, int]:
    seen = {}
    pcm = {}
    keys = {}
    problems = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        for mark in MARKERS:
            if mark in line:
                if mark in seen:
                    problems.append(f"duplicate {mark}")
                seen[mark] = line_number
        if "L6028_LAB_UNEXPECTED_DMA_REQUEST" in line:
            problems.append("unexpected DMA request")
        start = line.find("L6028_TAP ")
        if start < 0:
            continue
        items = line[start + len("L6028_TAP "):].split()
        if not items:
            continue
        props = dict(part.split("=", 1) for part in items[1:] if "=" in part)
        event = items[0]
        if event == "mix_output":
            try:
                frame, channel = int(props["frame"]), int(props["channel"])
                bits = int(props["f32bits"], 16)
                if not 0 <= channel < 10:
                    raise ValueError("invalid channel")
                key = (frame, channel)
                if key in pcm:
                    problems.append(f"duplicate output frame/channel {key}")
                pcm[key] = bits
            except (KeyError, ValueError) as exc:
                problems.append(f"bad mix output line {line_number}: {exc}")
        elif event == "key_on":
            try:
                keys[int(props["voice"])] = int(props["frame"])
            except (KeyError, ValueError) as exc:
                problems.append(f"bad key-on line {line_number}: {exc}")
    if set(seen) != set(MARKERS) or [seen.get(x, -1) for x in MARKERS] != sorted(seen.values()):
        problems.append("missing or out-of-order L6028_LAB_BEGIN/OVERLAP/DONE")
    if require_trace:
        if set(keys) < {0, 1}:
            problems.append("key-on tap missing for voice 0 or 1")
        elif keys[1] - keys[0] != 220:
            problems.append(f"voice trigger spacing = {keys[1] - keys[0]}, expected 220 frames")
        if not pcm:
            problems.append("no mix_output PCM taps")
        else:
            counts = {}
            for frame, channel in pcm:
                counts[frame] = counts.get(frame, 0) + 1
            missing = [frame for frame, n in counts.items() if n != 10]
            if missing:
                problems.append(f"incomplete 10-channel output in {len(missing)} frames")
            frame_indices = sorted(counts)
            if frame_indices != list(range(frame_indices[0], frame_indices[-1] + 1)):
                problems.append("gaps in output frames")
            if not any(bits & 0x7fffffff for (frame, ch), bits in pcm.items() if ch in (0, 1)):
                problems.append("all main output float32 values are zero")
    if problems:
        raise ValueError("; ".join(problems))
    return {"markers": len(seen), "output_samples": len(pcm),
            "output_frames": len({frame for frame, _ in pcm}), "key_ons": len(keys)}

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("errorlog", type=Path)
    ap.add_argument("--require-trace", action="store_true")
    args = ap.parse_args()
    try:
        result = verify(args.errorlog, args.require_trace)
    except (OSError, ValueError) as exc:
        ap.exit(1, f"L6028 FIXTURE FAIL: {exc}\n")
    print("L6028 FIXTURE PASS:", result)

if __name__ == "__main__":
    main()
