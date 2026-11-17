#!/usr/bin/env python3
"""Small stdlib-only regression checks for text L6028 capture protocol.

Run: python scripts/test_l6028_capture_protocol.py
This checks log parsing and schema only; it does NOT prove an audio/render build.
"""
from pathlib import Path
import importlib.util
import tempfile

script = Path(__file__).with_name("l6028_tap_summary.py")
spec = importlib.util.spec_from_file_location("l6028_tap_summary", script)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

fixture = """L6028_TAP select seq=0 tick=0 frame=0 offset=0 data=0100 mask=ffff
L6028_TAP register seq=1 tick=0 frame=0 voice=0 reg=1 word=0 data=1000 shadow=000000001000
L6028_TAP dma_request seq=2 tick=64 frame=0
L6028_TAP dma_write seq=3 tick=64 frame=0 byte_address=00000000 sample_type=0 data=1234
L6028_TAP mix_output frame=0 channel=0 f32bits=3f800000
L6028_TAP mix_output frame=0 channel=1 f32bits=00000000
"""
with tempfile.TemporaryDirectory() as td:
    path = Path(td) / "trace.log"
    path.write_text(fixture, encoding="utf-8")
    events = mod.load_events(path)
    assert len(events) == 6
    assert [e[0] for e in events[:4]] == ["select", "register", "dma_request", "dma_write"]
    assert [int(e[1]["seq"]) for e in events[:4]] == [0, 1, 2, 3]
    assert [int(e[1]["channel"]) for e in events[4:]] == [0, 1]
    assert events[4][1]["f32bits"] == "3f800000"
    assert {int(e[1]["frame"]) for e in events} == {0}
print("L6028 capture protocol parsing: PASS")
