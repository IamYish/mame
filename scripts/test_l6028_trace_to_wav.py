#!/usr/bin/env python3
"""Test that the exact IEEE754 bits survive the trace-to-WAV extraction."""
import importlib.util
import struct
import tempfile
from pathlib import Path

path = Path(__file__).with_name("l6028_trace_to_wav.py")
spec = importlib.util.spec_from_file_location("l6028_trace_to_wav", path)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

with tempfile.TemporaryDirectory() as td:
    d = Path(td)
    inp, out = d / "input.log", d / "out.wav"
    with inp.open("w", encoding="utf-8") as f:
        for frame in (10, 11):
            for ch in range(10):
                bits = (0x3f000000 if ch == 0 else 0xbf000000 if ch == 1 else 0)
                f.write(f"L6028_TAP mix_output frame={frame} channel={ch} f32bits={bits:08x}\n")
    frames, chans = mod.convert(inp, out, "stereo", 44100)
    assert (frames, chans) == (2, 2)
    wav = out.read_bytes()
    assert wav[:4] == b"RIFF"
    assert wav[8:12] == b"WAVE"
    assert struct.unpack_from("<H", wav, 20)[0] == 3
    assert struct.unpack_from("<I", wav, 44)[0] == 2
    assert struct.unpack_from("<I", wav, 52)[0] == 16
    assert struct.unpack_from("<IIII", wav, 56) == (0x3f000000, 0xbf000000) * 2
    # A missing output channel is a hard failure, not silence that can be invented.
    inp.write_text("L6028_TAP mix_output frame=0 channel=0 f32bits=00000000\n", encoding="utf-8")
    try:
        mod.convert(inp, out, "stereo")
    except ValueError as exc:
        assert "Incomplete" in str(exc)
    else:
        raise AssertionError("Incomplete source trace accepted")
print("L6028 exact float32 WAV extraction: PASS")
