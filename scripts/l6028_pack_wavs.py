#!/usr/bin/env python3
"""Pack eight 44100-Hz mono signed PCM16 WAVs as a private L6028 lab image.

Usage: py scripts/l6028_pack_wavs.py "samples 2.zip" --output "l6028_samples.bin"
Binary format: "L6028PK1" (8 bytes); u32 count=8, u32 reserved=0;
8 pairs of little-endian u32 (actual_frames,padded_frames); then all PCM16-LE
tracks in numeric filename order, individually zero-padded to multiples of 16
and protected by at least sixteen extra zero samples.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import re
import struct
import wave
import zipfile
from pathlib import Path

MAGIC = b"L6028PK1"
COUNT = 8
MAX_FRAMES = 0x8000 - 16

def convert(source: Path, output: Path, manifest: Path | None = None) -> dict:
    if not zipfile.is_zipfile(source):
        raise ValueError("Expected ZIP archive with eight mono PCM16 WAVs")
    with zipfile.ZipFile(source) as archive:
        found = []
        for name in archive.namelist():
            basename = Path(name).name
            if name.startswith("__MACOSX/") or basename.startswith("._") or not basename.lower().endswith(".wav"):
                continue
            m = re.match(r"^\s*(\d{1,2})\b", basename)
            if not m:
                raise ValueError(f"WAV filename needs numbered 1..8 prefix: {name}")
            found.append((int(m.group(1)), name, archive.read(name)))
    found.sort(key=lambda item: item[0])
    if [item[0] for item in found] != list(range(1, COUNT + 1)):
        raise ValueError("Expected exactly eight uniquely numbered WAV files (1..8)")
    records, payloads, details = [], [], []
    for pad, name, content in found:
        try:
            with wave.open(io.BytesIO(content), "rb") as wav:
                fmt = (wav.getnchannels(), wav.getframerate(), wav.getsampwidth(), wav.getcomptype())
                frames = wav.getnframes()
                pcm = wav.readframes(frames)
        except wave.Error as e:
            raise ValueError(f"Bad WAV {name}: {e}") from e
        if fmt != (1, 44100, 2, "NONE"):
            raise ValueError(f"Require 44100Hz mono signed PCM16 WAV: {name}")
        if not 0 < frames <= MAX_FRAMES or len(pcm) != 2 * frames:
            raise ValueError(f"Bad PCM frame length for L6028 slot: {name}")
        padded = ((frames + 16 + 15) // 16) * 16
        records.append((frames, padded))
        payloads.append(pcm + bytes(2 * (padded - frames)))
        details.append({"pad": pad, "name": Path(name).name, "frames": frames,
                        "start_word": 0x1000 + (pad - 1) * 0x8000,
                        "pcm_sha256": hashlib.sha256(pcm).hexdigest()})
    packed = MAGIC + struct.pack("<II", COUNT, 0)
    packed += b"".join(struct.pack("<II", *r) for r in records)
    packed += b"".join(payloads)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(packed)
    info = {"sample_rate": 44100, "channels_per_file": 1, "bits": 16,
            "pack_sha256": hashlib.sha256(packed).hexdigest(), "samples": details}
    if manifest:
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps(info, indent=2)+"\n", encoding="utf-8")
    return info

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("archive", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--manifest", type=Path)
    a=p.parse_args()
    info=convert(a.archive, a.output, a.manifest)
    print(f"Packed {len(info['samples'])} PCM16 samples without conversion; SHA256 {info['pack_sha256']}")

if __name__ == "__main__":
    main()
