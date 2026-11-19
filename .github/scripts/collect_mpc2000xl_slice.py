#!/usr/bin/env python3
"""Package the actual source/header inputs used by a successful original MPC2000XL MAME build.

This is an extraction snapshot, NOT a validated independent build and NOT a pure-C port.
The compiler-generated .d files are the authoritative primary dependency source.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
REQUIRED = (
    "src/mame/akai/mpc2000.cpp",
    "src/devices/cpu/nec/v5x.cpp",
    "src/devices/cpu/upd7810/upd7810.cpp",
    "src/devices/sound/l7a1045_l6028_dsp_a.cpp",
    "src/emu/schedule.cpp",
    "src/emu/diexec.cpp",
)
SUPPORT = (
    "makefile",
    "scripts/genie.lua",
    "scripts/build/makedep.py",
    "scripts/src/emu.lua",
    "scripts/src/main.lua",
    "scripts/src/lib.lua",
    "scripts/src/formats.lua",
    "scripts/src/cpu.lua",
    "scripts/src/machine.lua",
    "scripts/src/sound.lua",
    "scripts/src/bus.lua",
    "src/mame/layout/mpc2000xl.lay",
    "COPYING",
)

def inside_repo(path: Path) -> Path | None:
    try:
        path = path.resolve(strict=True)
        path.relative_to(ROOT)
    except (ValueError, FileNotFoundError, OSError):
        return None
    return path if path.is_file() else None

def dep_tokens(dep_file: Path) -> list[str]:
    data = dep_file.read_text(encoding="utf-8", errors="replace")
    data = re.sub(r"\\\r?\n", " ", data)
    # -MP may append separate empty header targets. Only read the first rule.
    data = re.split(r"\n[^\n]*:\s*(?:\n|$)", data, maxsplit=1)[0]
    if ":" not in data:
        return []
    prerequisites = data.split(":", 1)[1]
    try:
        return shlex.split(prerequisites, posix=True)
    except ValueError:
        return prerequisites.split()

def resolve_token(token: str, dep_file: Path) -> Path | None:
    if not token or token == "\\" or token.endswith(":"):
        return None
    path = Path(token)
    if path.is_absolute():
        return inside_repo(path)
    # MAME's generated Makefiles typically compile from build/projects/<os>/mame.
    # Search only plausible compilation working directories, not source-tree
    # directory sweeps that would reintroduce unrelated machines.
    bases = [ROOT, ROOT / "build/projects/sdl/mame", ROOT / "build/projects/sdl3/mame"]
    bases.extend(list(dep_file.parents)[:7])
    for base in bases:
        hit = inside_repo(base / path)
        if hit is not None:
            return hit
    return None

def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("dist/mpc2000xl-source-slice"))
    args = ap.parse_args()
    dest = (ROOT / args.out).resolve()
    dest.mkdir(parents=True, exist_ok=True)

    dep_files = sorted((ROOT / "build").rglob("*.d"))
    if not dep_files:
        raise SystemExit("ERROR: no compiler .d dependency files found; cannot claim a traced slice.")

    selected: set[Path] = set()
    unmatched: set[str] = set()
    for dep_file in dep_files:
        for token in dep_tokens(dep_file):
            hit = resolve_token(token, dep_file)
            if hit is not None:
                selected.add(hit)
            elif token and (token.startswith("src/") or "/src/" in token):
                unmatched.add(token)

    for rel in SUPPORT:
        hit = inside_repo(ROOT / rel)
        if hit is not None:
            selected.add(hit)

    rels = {p.relative_to(ROOT).as_posix() for p in selected}
    missing = [p for p in REQUIRED if p not in rels]
    if missing:
        raise SystemExit(
            "ERROR: expected original MPC machine inputs absent from dependency trace: "
            + ", ".join(missing)
            + ". No success artifact will be claimed."
        )

    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    entries = []
    for p in sorted(selected, key=lambda x: x.relative_to(ROOT).as_posix()):
        rel = p.relative_to(ROOT).as_posix()
        entries.append({
            "path": rel,
            "bytes": p.stat().st_size,
            "sha256": digest(p),
            "category": "build-generated" if rel.startswith("build/") else
                        "machine" if rel.startswith("src/mame/akai/") else
                        "device" if rel.startswith("src/devices/") else
                        "framework" if rel.startswith("src/emu/") else
                        "third-party" if rel.startswith("3rdparty/") else
                        "support",
        })

    source_count = sum(Path(p["path"]).suffix.lower() in {".c", ".cc", ".cpp", ".cxx", ".s"} for p in entries)
    if source_count < 20:
        raise SystemExit(f"ERROR: only {source_count} translation units observed; refusing incomplete slice.")

    counts = dict(sorted(collections.Counter(p["category"] for p in entries).items()))
    manifest = {
        "repository": "IamYish/mame",
        "commit": sha,
        "original_driver": "src/mame/akai/mpc2000.cpp",
        "status": "compiler-input-source-snapshot; not independently build-verified",
        "language": "MAME C++ source; C translation is a later phase",
        "roms_included": False,
        "method": "successful targeted MAME build + compiler dependency files",
        "dependency_file_count": len(dep_files),
        "source_translation_unit_count": source_count,
        "file_count": len(entries),
        "category_counts": counts,
        "unresolved_in_repo_tokens": sorted(unmatched)[:500],
        "files": entries,
    }
    report = [
        "Original MPC2000XL MAME source slice",
        f"Repository: {manifest['repository']}",
        f"Commit: {sha}",
        "Driver: src/mame/akai/mpc2000.cpp (not diagnostic fork)",
        f"Compiler .d files: {len(dep_files)}",
        f"Translation units: {source_count}",
        f"Packaged files: {len(entries)}",
        f"Categories: {counts}",
        "",
        "This is a trace-derived source snapshot, not a proven standalone build.",
        "No proprietary Akai ROMs are collected.",
        "Retain source-file license notices. MAME build/link licenses remain applicable.",
        "The archive includes generated headers actually named by compiler dependencies.",
        "Other optional build generator inputs or external system libraries may be",
        "needed for a later standalone build; inspect manifest and build log.",
        "",
        "Unresolved source-like dependency tokens (first 500):",
        *sorted(unmatched)[:500],
    ]
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (dest / "README.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    (dest / "files.txt").write_text("\n".join(e["path"] for e in entries) + "\n", encoding="utf-8")

    if args.log.is_file():
        lines = args.log.read_text(encoding="utf-8", errors="replace").splitlines()
        (dest / "build-log-tail.txt").write_text(
            "\n".join(lines[-350:]) + "\n", encoding="utf-8"
        )

    archive = dest / "mpc2000xl-source-slice.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as z:
        for p in sorted(selected, key=lambda x: x.relative_to(ROOT).as_posix()):
            z.write(p, p.relative_to(ROOT).as_posix())
        for name in ("manifest.json", "README.txt", "files.txt", "build-log-tail.txt"):
            path = dest / name
            if path.exists():
                z.write(path, "_slice_metadata/" + name)

    print(f"Created {archive} ({archive.stat().st_size:,} bytes) with {len(entries)} files")
    return 0

if __name__ == "__main__":
    sys.exit(main())
