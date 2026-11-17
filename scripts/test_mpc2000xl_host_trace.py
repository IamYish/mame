#!/usr/bin/env python3
"""Synthetic log tests, no original Akai firmware or user RAM is included."""
import importlib.util
import tempfile
from pathlib import Path

modpath = Path(__file__).with_name("mpc2000xl_host_trace.py")
spec = importlib.util.spec_from_file_location("mpc2000xl_host_trace", modpath)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

with tempfile.TemporaryDirectory() as folder:
    p = Path(folder) / "synthetic.log"
    raw = (
        "MPCXL_HOST seq=0 tick=768 dir=write port=0080 data=0000 mask=ffff "
        "pc=0004187c es=2000 bx=0040\n"
        "MPCXL_DESCRIPTOR_CANDIDATE tick=768 pc=0004187c es=2000 bx=0040 "
        "physical_candidate=00020040 bytes=" + "ab" * 48 + "\n"
        "MPCXL_HOST seq=1 tick=960 dir=read port=0088 data=0000 mask=ffff pc=0003e590\n"
        "MPCXL_HOST seq=2 tick=961 dir=write port=0088 data=0100 mask=ffff "
        "pc=0003e599 es=2000 bx=0040\n"
    )
    p.write_text(raw)
    events, desc = mod.parse(p)
    assert len(events) == 3 and len(desc) == 1
    assert events[0]["port"] == 0x80 and events[2]["data"] == 0x0100
    assert desc[0]["bytes_hex"] == "ab" * 48
    assert desc[0]["verification"] == "candidate_only_not_proven_note_descriptor"
    p.write_text(raw.replace("seq=2", "seq=0"))
    try:
        mod.parse(p)
    except ValueError as e:
        assert "non-monotonic" in str(e)
    else:
        raise AssertionError("duplicate sequence not rejected")
print("MPC2000XL passive port trace parser tests: PASS")
