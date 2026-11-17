# MPC2000XL original OS runtime capture experiment

## Boundaries

This is an **additional** V53A board driver, `mpc2000xldiag`, on the existing `lab/l6028-capture` branch. The existing two-voice `l6028lab` and original `l7a1045_l6028_dsp_a.cpp` playback equations are unchanged.

Source derived with BSD-3-Clause attribution from [dariuszchynek/mpc2000xl-emulator](https://github.com/dariuszchynek/mpc2000xl-emulator), upstream commit `a2d8ae470c730df9501b7c14ab4ebc94d32a5e08`. Its developer reports **native MPC2000XL OS 1.20 boot to MAIN** on macOS, with high-level panel serial input, but **NOT** verified sampling or PCM playback. This imported driver still has to compile and run in our fork.

OS 1.14 and 1.20 uploaded privately: exact SHA-1 identities `f272ef2b1948730446fe260e4c0c830884832d3a` and `382be688972fe3d85caeca99abff4b6c391347fb`. Both are 524288 bytes, have `FC00:0400` reset vectors and pass their own ROM word-sum checksum. The quickloader checks these identities. Neither firmware nor panel ROM is in GitHub.

## Passive raw L6028 host traffic

Set `MPCXL_HOST_CAPTURE=1` to install passive CPU I/O taps at ports 0x80–0x8f. For every read or write the capture logs original 16-bit value, bit mask, port, operation order, emulated oscillator tick, CPU PC, plus ES/BX on writes. No callback changes the I/O data or delays/emulates sound.

At the known initializer register-0 select locations, OS 1.14 at file offset `0x4127A` or 1.20 at `0x4187A`, a separate record attempts to snapshot 48 bytes from CPU RAM using candidate ES:BX. This is called `MPCXL_DESCRIPTOR_CANDIDATE` because V53 XA address translation and code relocation have not been established by executing this driver. Correlate with PC and subsequent host writes before calling it a real note descriptor.

To truly meet the goal, we must boot OS, load a real sample/program by *guest* machinery, trigger a pad through its serial protocol, and observe a descriptor and subsequent 0x88 key-on writes. Eight synthetic pack WAVs in the other fixture **do not meet** this requirement.

## Linux ROM-local launch

Build using CI or focused MAME source build. Keep the ROM outside version control. In the same directory as the built binary:

```bash
mkdir -p /private/mpcxl
# Place the real MPC2KXL.BIN there; no ROM files may be uploaded to GitHub.
MPCXL_HOST_CAPTURE=1 ./mpc2000xldiag mpc2000xldiag \
   -quickload /private/mpcxl/MPC2KXL.BIN \
   -log -video none -sound none -nothrottle -seconds_to_run 8
```

The first run is strictly a **boot and I/O observational test**; headless execution is not a note trigger. MAME's `error.log` and future descriptor dumps are private and must never be automatically uploaded by GitHub Actions. CI builds a ROM-free executable only.

## Limitations

- The high-level panel emulator substitutes for the separate panel MCU ROM and has approximate timing.
- Original Akai image checksums authenticate an image, **not** successful execution.
- PC-to-image offset versus runtime location must be verified from the trap output before treating a 48-byte RAM dump as the note descriptor.
- Audio, sample loading from a floppy, guest program creation, the OS 1.14 boot path and descriptor capture are **unverified** until live execution.
- Input PCM is intentionally **not** a golden output. No input/output matching and no DSP equation modifications.

The first descriptor encountered may be a boot initialization slot rather than an audible note. Retain **multiple** candidate snapshots, then associate them with a subsequent key-on and sample-memory evidence. Never mislabel a boot-initialization descriptor as the triggered sample's descriptor.

## Attempt one real sample and pad event in a LOCAL interactive session

The companion private FAT12 floppy image `MPC2000XL_KICK_FAT12.img` contains `KICK.WAV` from the user's original sample pack, with its WAV bytes preserved. This image is NOT a repository artifact, and guest compatibility remains unverified.

For an interactive Linux MAME build, invoke:

```bash
MPCXL_HOST_CAPTURE=1 ./mpc2000xldiag mpc2000xldiag \
  -quickload /private/mpcxl/MPC2KXL.BIN \
  -flop1 /private/mpcxl/MPC2000XL_KICK_FAT12.img \
  -log -window -sound none
```

The guest must first boot successfully, then **guest firmware** must load the floppy WAV, create/assign an actual note/program, and receive a pad press via the modeled serial panel input. This has not yet been demonstrated on this imported driver. A test with no guest sample/program loaded is not sufficient for the objective.

After exiting MAME, inspect the private `error.log` using:

```bash
python3 scripts/mpc2000xl_host_trace.py error.log --out private/mpc2000xl-host.jsonl --require-host-writes
```

Do not mark success until `MPCXL_DESCRIPTOR_CANDIDATE` corresponds to the note-init routine and the generated port tape contains the original firmware's key-on. To confirm an **audible** note, additionally establish valid sample-memory contents and a nonzero chip sample/output event; a register write alone does not prove a sample was produced. Keep all private logs outside Git.
