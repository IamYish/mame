#!/usr/bin/env python3
"""Validate marker and PCM-capture test logic using artificial logs only."""
import importlib.util
from pathlib import Path
import tempfile

f = Path(__file__).with_name("l6028_fixture_check.py")
spec = importlib.util.spec_from_file_location("l6028_fixture_check", f)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

with tempfile.TemporaryDirectory() as folder:
    p = Path(folder) / "error.log"
    lines = ["L6028_LAB_BEGIN sample_rate=44100 words=4096",
             "L6028_TAP key_on frame=1 voice=0 start=00001000 end=00002000 step=1000",
             "L6028_LAB_OVERLAP voice=1",
             "L6028_TAP key_on frame=221 voice=1 start=00003000 end=00004000 step=1000"]
    for frame in range(3):
        for ch in range(10):
            bits = 0x3f000000 if ch == 0 else 0
            lines.append(f"L6028_TAP mix_output frame={frame} channel={ch} f32bits={bits:08x}")
    lines.append("L6028_LAB_DONE voices=2")
    p.write_text("\n".join(lines), encoding="utf-8")
    assert mod.verify(p, True)["output_frames"] == 3
    p.write_text("\n".join(lines[:-1]), encoding="utf-8")
    try:
        mod.verify(p, True)
        raise AssertionError("Missing completion was accepted")
    except ValueError:
        pass
print("L6028 fixture checker synthetic tests: PASS")
