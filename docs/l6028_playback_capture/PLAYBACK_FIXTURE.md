# ROM-free L6028 playback fixture

Source: `src/mame/akai/l6028lab.cpp`. Machine: `l6028lab`.

The fixture instantiates the **same MAME L6028 device** as the MPC2000XL driver with its exact 33.8688 MHz clock (44.1 kHz audio). It does not emulate the MPC operating system, V53 CPU, sequencer, or DAC. A diagnostic `lab_host_w` method dispatches host bus writes to the L6028's **existing** register handlers; none of its interpolation, filter, envelope, gain or mix equations were replaced.

## First deterministic stimulus

- The fixture loads two 4096-word signed 16-bit integer patterns directly into the normal L6028 RAM address space at word addresses `0x1000` and `0x3000`.
- Voice 0 starts after 1 frame. Voice 1 starts **220 virtual output frames later**. They overlap.
- All eight chip registers for each voice are written as three 16-bit words: unity pitch increment `0x1000` (4.12), envelope level/target `0xffff`, L/R gains `0xff`, cutoff `0x7fff`, no send and a full-length loop. Filters remain active.
- After another 2048 frames, the existing sound updater is flushed and MAME exits.

This is *not* yet the 16-sample listening kit. It is a finite, deterministic two-voice validation fixture.

## Building and running under MSYS2/MinGW (Windows)

The MAME build is normally made using its MSYS2 toolchain, not only Visual Studio Build Tools. In the branch root, try:

```bash
make -j8 SOURCES=src/mame/akai/l6028lab.cpp SUBTARGET=l6028lab
```

The Linux source-filtered build linked the executable as `l6028lab` in GitHub Actions. Example:

```bash
./l6028lab l6028lab -log -seconds_to_run 1 -nothrottle -video none -wavwrite l6028-mame-mix.wav
```

Alternatively use `./mame l6028lab ...` if building the normal MAME target. In `error.log`, verify `L6028_LAB_BEGIN`, `L6028_LAB_OVERLAP` and `L6028_LAB_DONE`. The first trace is a **MAME mixer output**, not a verified Akai DAC-input capture.

For optional diagnostic ten-channel PCM tracing, enable `L6028_CAPTURE_TRACE=1` **when compiling `l7a1045_l6028_dsp_a.cpp`**, not only in the fixture driver; the macro is intentionally off in normal builds. Then use `scripts/l6028_trace_to_wav.py` with the `-log` output.

## Gates / disclaimers

1. Build compiles; fixture log reaches all three phases.
2. Mixed audio includes nonzero samples and a second voice at 220-frame spacing.
3. Compare trace-enabled and trace-disabled PCM with identical input events.
4. Use registered reference behavior to drive a separately controlled audio engine later.
5. Eventually use the user's full 16-sample kit for presentation listening.

**Current status**: source committed, build/audio not yet independently verified. MAME's interpolation and filter arithmetic are a reconstruction; the chip's true internal precision has not been established. The original Akai firmware is not used.

## Automated log acceptance

After running the MAME fixture, validate the test milestones:

```powershell
py scripts/test_l6028_fixture_check.py
py scripts/l6028_fixture_check.py error.log
py scripts/l6028_fixture_check.py error.log --require-trace
```

The final command requires a capture-enabled DSP build, verifies both key-on events are separated by 220 internal audio frames, checks ten complete output channels and rejects all-silent main PCM. These scripts have **not** executed the MAME machine or established a bit-exact hardware result. The diagnostic MAME machine is registered without MAME's `MACHINE_NOT_WORKING` warning screen to allow headless validation; research limitations still apply.

## Automated GitHub Actions build / PCM gate

The optional branch-scoped workflow [`l6028-playback-proof.yml`](../../../.github/workflows/l6028-playback-proof.yml) is committed alongside this fixture. On push to `lab/l6028-capture`, if GitHub Actions are enabled for the fork, it installs Linux MAME dependencies, runs the Python tests, compiles **only the L6028 diagnostic driver**, executes its two-voice test, and uploads the machine log and exact MAME float32 stereo/all-10-channel WAV files.

The build uses `ARCHOPTS=-DL6028_CAPTURE_TRACE=1` to enable taps in the actual L6028 translation unit. It does **not** upload proprietary firmware or assert silicon identity. A green workflow is needed before claiming the rendered PCM path works. To compare trace-on versus trace-off, follow with the same build with no `ARCHOPTS` define and compare exact output bits; the workflow does not do that additional differential build yet.

Check `Actions → L6028 ROM-free PCM playback proof` in GitHub. If no run is recorded, use the documented MSYS2 local build instead. This workflow has no background agent; it runs only through GitHub's own Actions service.

## Native build outcome 1 — API compatibility correction

The first GitHub Actions build failed when compiling the lab driver, before any sound was generated:
`WRITE_LINE_MEMBER(dma_request)` is no longer a valid declaration in this pinned MAME revision. The callback is now a normal `void dma_request(int state)` member, matching other MAME driver callback implementations. The original L6028 playback arithmetic is unchanged. Re-run the focused workflow and inspect the next build error or PCM evidence; no success is claimed merely from correcting source.

## Native build outcome 2 — compiler and linker PASS

The follow-up job (GitHub Actions run `44086925666`, commit `93cb8289`) successfully compiled `src/mame/akai/l6028lab.cpp` **and** `l7a1045_l6028_dsp_a.cpp`, generated exactly one driver and linked `l6028lab`. Runtime inspection failed with exit code 127 only because the workflow invoked `./mamel6028lab`, which is not the linked filename. The dedicated CI now executes `./l6028lab` and copies `error.log` for diagnosis even when a runtime error occurs. No audio was rendered during the preceding failed CI run.

## Native build outcome 3 — runtime argument corrected

In Actions run `44089441552` at commit `78ef357e`, the lab's C++ code compiled, linked and passed `./l6028lab -listfull l6028lab`. The subsequent run ended with exit code 3 and its retained `console.log` contained only `Error: unknown option: 0`. This came from using the unsupported `-throttle 0` command syntax. The next run uses MAME's supported `-nothrottle` switch. The machine had **not started processing PCM** in the failed run.
