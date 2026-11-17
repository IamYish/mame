#!/usr/bin/env python3
"""Unit tests for MPC2000XL firmware recognition, ZIP discovery and fail-closed staging."""
from __future__ import annotations

import hashlib
import importlib.util
import tempfile
import zipfile
import zlib
from pathlib import Path

path = Path(__file__).with_name("mpc2000xl_rom_audit.py")
spec = importlib.util.spec_from_file_location("mpc2000xl_rom_audit", path)
assert spec and spec.loader
rom = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rom)

# Test without redistributing or embedding proprietary ROM bytes.
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    fake_os = b"test-os" * 128
    fake_panel = b"test-panel" * 128
    def fake_spec(data: bytes) -> tuple[int, str, str, str, str]:
        return (len(data), f"{zlib.crc32(data):08x}", hashlib.sha1(data).hexdigest(),
                "Synthetic test", "test")
    rom.ROM_SPECS = {"test_os.bin": fake_spec(fake_os), rom.PANEL_NAME: fake_spec(fake_panel)}
    assert rom.recognize(fake_os) == "test_os.bin"
    assert rom.recognize(b"other payload") is None
    os_path = root / "random_name.BIN"
    os_path.write_bytes(fake_os)
    fake_zip = root / "nested.zip"
    with zipfile.ZipFile(fake_zip, "w") as archive:
        archive.writestr("another_name.PRG", fake_panel)
        archive.writestr("noise.dat", b"unrecognized")
    found, ignored = rom.inspect([os_path, fake_zip])
    assert len(found) == 2 and len(ignored) == 1
    assert rom.public_report(found, ignored)["complete_for_selected_bios"]
    packaged = root / "local-roms" / "mpc2000xl.zip"
    rom.stage(found, packaged)
    with zipfile.ZipFile(packaged) as archive:
        assert set(archive.namelist()) == {"test_os.bin", rom.PANEL_NAME}
        assert archive.read(rom.PANEL_NAME) == fake_panel
    # No panel -> do not write a deceptively usable archive.
    incomplete = root / "should_not_exist.zip"
    try:
        rom.stage({"test_os.bin": fake_os}, incomplete)
        raise AssertionError("Expected incomplete staging refusal")
    except ValueError:
        assert not incomplete.exists()
print("MPC2000XL ROM audit synthetic tests: PASS")
