#!/usr/bin/env python3
"""Convert MAME L6028_TAP mix_output records to lossless float32 WAV.

Examples:
  python scripts/l6028_trace_to_wav.py error.log --output mpc_main_f32.wav
  python scripts/l6028_trace_to_wav.py error.log --output mpc_all10_f32.wav --channels all

PCM values are NOT converted, normalized, resampled, or clipped. The WAV contains
MAME float32 sample bit patterns, *not verified original Akai DAC-input PCM*.
"""
from __future__ import annotations

import argparse
import struct
from pathlib import Path

MARKER = "L6028_TAP mix_output "

def convert(log: Path, output: Path, channels: str = "stereo", rate: int = 44100) -> tuple[int, int]:
    if rate <= 0:
        raise ValueError("Sample rate must be positive")
    selected = (0, 1) if channels == "stereo" else tuple(range(10))
    if channels not in {"stereo", "all"}:
        raise ValueError("channels must be 'stereo' or 'all'")
    channel_count = len(selected)
    frame_count = 0
    frame_id: int | None = None
    previous_frame: int | None = None
    values: dict[int, int] = {}

    with log.open("r", encoding="utf-8", errors="replace") as source, output.open("wb") as dest:
        # WAVE_FORMAT_IEEE_FLOAT, with a fact chunk for non-PCM compatibility.
        dest.write(b"RIFF" + struct.pack("<I", 0) + b"WAVE")
        dest.write(b"fmt " + struct.pack("<IHHIIHH", 16, 3, channel_count,
                                         rate, rate * channel_count * 4, channel_count * 4, 32))
        dest.write(b"fact" + struct.pack("<II", 4, 0))
        dest.write(b"data" + struct.pack("<I", 0))

        def write_frame() -> None:
            nonlocal frame_count, previous_frame
            if frame_id is None:
                return
            if set(values) != set(range(10)):
                raise ValueError(f"Incomplete 10-channel frame {frame_id}: channels {sorted(values)}")
            if previous_frame is not None and frame_id != previous_frame + 1:
                raise ValueError(f"Non-contiguous frame index: {previous_frame} -> {frame_id}")
            dest.write(struct.pack("<" + "I" * channel_count, *(values[ch] for ch in selected)))
            frame_count += 1
            previous_frame = frame_id

        for line_no, line in enumerate(source, 1):
            start = line.find(MARKER)
            if start < 0:
                continue
            fields = line[start + len(MARKER):].split()
            props = dict(field.split("=", 1) for field in fields if "=" in field)
            try:
                current = int(props["frame"])
                channel = int(props["channel"])
                bits = int(props["f32bits"], 16)
            except (KeyError, ValueError) as exc:
                raise ValueError(f"Malformed mix_output at line {line_no}") from exc
            if channel not in range(10) or not 0 <= bits <= 0xffffffff:
                raise ValueError(f"Invalid channel or sample at line {line_no}")
            if frame_id is None:
                frame_id = current
            elif current != frame_id:
                write_frame()
                frame_id = current
                values.clear()
            if channel in values:
                raise ValueError(f"Duplicate channel {channel}, frame {current}, line {line_no}")
            values[channel] = bits

        write_frame()
        if not frame_count:
            raise ValueError("No mix_output records: capture may be disabled or no stream was rendered")
        end = dest.tell()
        if end > 0xffffffff - 8:
            raise ValueError("Diagnostic file is too large for classic RIFF/WAV")
        dest.seek(4)
        dest.write(struct.pack("<I", end - 8))
        dest.seek(44)
        dest.write(struct.pack("<I", frame_count))
        dest.seek(52)
        dest.write(struct.pack("<I", end - 56))
    return frame_count, channel_count

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("logfile", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--channels", choices=("stereo", "all"), default="stereo")
    ap.add_argument("--rate", type=int, default=44100)
    args = ap.parse_args()
    try:
        frames, channels = convert(args.logfile, args.output, args.channels, args.rate)
    except Exception:
        args.output.unlink(missing_ok=True)
        raise
    print(f"Wrote {frames} frames, {channels} channels, {args.rate} Hz, float32 WAV: {args.output}")

if __name__ == "__main__":
    main()
