#!/usr/bin/env python3
"""Identify privately supplied MPC2000XL ROMs and, when complete, stage a MAME ZIP.

No firmware is downloaded, embedded, or uploaded to GitHub. Fingerprints are
from src/mame/akai/mpc2000.cpp at the lab's pinned MAME revision.

Examples:
    py scripts/mpc2000xl_rom_audit.py MPC2KXL.BIN "mpc2kxl.zip"
    py scripts/mpc2000xl_rom_audit.py MPC2KXL.BIN "mpc2kxl.zip" --json
    py scripts/mpc2000xl_rom_audit.py MPC2KXL.BIN "mpc2kxl.zip" PANEL.ROM \
        --stage local-roms/mpc2000xl.zip
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
import zlib
from pathlib import Path

# MAME filename -> (bytes, CRC32, SHA-1, description, BIOS selector).
ROM_SPECS: dict[str, tuple[int, str, str, str, str]] = {
    "mpc2000xl_120.bin": (
        0x80000, "c082f188", "382be688972fe3d85caeca99abff4b6c391347fb",
        "V53 main OS 1.20", "default"
    ),
    "mpc2000xl_114.bin": (
        0x80000, "7b4fe8af", "f272ef2b1948730446fe260e4c0c830884832d3a",
        "V53 main OS 1.14", "ver114"
    ),
    "mpc2000xl_112.bin": (
        0x80000, "552f660a", "91d1a1bb5aaa0b98538b4b47567c59770ba9a356",
        "V53 main OS 1.12", "ver112"
    ),
    "mpc2000xl_111.bin": (
        0x80000, "0c232258", "3dd6481c9ced76baa8990580a23aec7c3aa9a1d1",
        "V53 main OS 1.11", "ver111"
    ),
    "mpc2000xl_110.bin": (
        0x80000, "12700bee", "dee8833a55b065cd81f34bf5ab60a2bcc29df0dcf26c9f1",
        "V53 main OS 1.10", "ver110"
    ),
    "mpc2000xl_107.bin": (
        0x80000, "3bc97b99", "2653b08245cc0d223bff24bc6da8c4817e39095c",
        "V53 main OS 1.07", "ver107"
    ),
    "akai mpc2000xl op v1_0.bin": (
        0x8000, "24382ade", "b02ca9b8a4ae41f4414e12d5188f638dbb99f36c",
        "uPD78C10 panel-controller ROM", "required"
    ),
}

PANEL_NAME = "akai mpc2000xl op v1_0.bin"


def fingerprint(data: bytes) -> tuple[int, str, str]:
    return len(data), f"{zlib.crc32(data):08x}", hashlib.sha1(data).hexdigest()


def recognize(data: bytes) -> str | None:
    fp = fingerprint(data)
    return next((name for name, spec in ROM_SPECS.items() if fp == spec[:3]), None)


def inspect(paths: list[Path]) -> tuple[dict[str, bytes], list[str]]:
    found: dict[str, bytes] = {}
    unmatched: list[str] = []
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as archive:
                members = [
                    (info.filename, archive.read(info))
                    for info in archive.infolist()
                    if not info.is_dir()
                ]
        else:
            members = [(path.name, path.read_bytes())]
        for member_name, data in members:
            name = recognize(data)
            if name is None:
                unmatched.append(f"{path.name}:{member_name}")
                continue
            if name in found and found[name] != data:
                raise ValueError(f"Conflicting contents for identified ROM {name}")
            found[name] = data
    return found, unmatched


def public_report(found: dict[str, bytes], unmatched: list[str]) -> dict[str, object]:
    bios = sorted(name for name in found if name != PANEL_NAME)
    return {
        "machine": "MAME mpc2000xl (NOT original non-XL MPC2000)",
        "matched": [
            {"mame_filename": name, "description": ROM_SPECS[name][3],
             "bios": ROM_SPECS[name][4], "size": ROM_SPECS[name][0],
             "crc32": ROM_SPECS[name][1], "sha1": ROM_SPECS[name][2]}
            for name in sorted(found)
        ],
        "unmatched_input_members": unmatched,
        "main_bios_found": bool(bios),
        "panel_rom_found": PANEL_NAME in found,
        "complete_for_selected_bios": bool(bios) and PANEL_NAME in found,
        "notes": [
            "A matching checksum proves ROM identity, not functional boot.",
            "MAME's MPC2000XL driver is marked MACHINE_NOT_WORKING.",
            "No ROM bytes are recorded in this report.",
        ],
    }


def stage(found: dict[str, bytes], target: Path) -> None:
    mains = [name for name in found if name != PANEL_NAME]
    if not mains:
        raise ValueError("No matching MPC2000XL main CPU firmware supplied")
    if PANEL_NAME not in found:
        raise ValueError("Required 32 KiB panel-controller ROM is missing; refusing partial MAME archive")
    target.parent.mkdir(parents=True, exist_ok=True)
    # MAME reads the archived payloads under these *exact* filename spellings.
    with zipfile.ZipFile(target, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(found):
            archive.writestr(name, found[name])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", metavar="FILE_OR_ZIP", nargs="+", type=Path,
                        help="Private local files; ZIP archives are searched by contents")
    parser.add_argument("--json", action="store_true", help="Emit hash-only JSON report")
    parser.add_argument("--stage", metavar="ZIP", type=Path,
                        help="Write complete local MAME ROM ZIP (requires panel ROM)")
    args = parser.parse_args(argv)
    try:
        found, unknown = inspect(args.inputs)
        report = public_report(found, unknown)
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            for item in report["matched"]:
                print(f"FOUND {item['description']}: {item['mame_filename']} "
                      f"({item['size']} bytes, CRC32 {item['crc32']})")
            if unknown:
                print(f"Unmatched members: {len(unknown)}")
            print("Panel-controller ROM:", "FOUND" if report["panel_rom_found"] else "MISSING")
            print("Complete ROM set:", "YES" if report["complete_for_selected_bios"] else "NO")
        if args.stage:
            stage(found, args.stage)
            print(f"Staged PRIVATE MAME ROM ZIP: {args.stage}", file=sys.stderr)
        return 0
    except (FileNotFoundError, OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"ROM audit error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
