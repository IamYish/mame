# L6028 playback-engine capture (reference-first)

Status: **CPU→DSP input, DMA, per-voice, and ten-channel post-mix taps committed; not yet compiled or PCM-validated**. This is **not** a new sampler implementation. The complete original MAME source tree is preserved on the fork's `master`; this branch is an isolated capture lab.

## Pinned reference

- Repository: `IamYish/mame`; upstream `mamedev/mame`.
- Base commit: `19b605cf64f8d8ee10b169f49cb774b0efe46ddd` (both branches matched when the capture branch was created).
- Unmodified reference device: `src/devices/sound/l7a1045_l6028_dsp_a.cpp` and `.h`.
- Original MPC2000 wiring: `src/mame/akai/mpc2000.cpp`.
- Additional driver reference: `src/mame/akai/mpc3000.cpp`; `src/mame/akai/s3000.cpp`.
- The device's own source carries BSD-3-Clause attribution; retain that attribution and MAME's applicable license notices for redistribution.

## Architectural boundary

The MPC's V53 CPU programs the L6028 through the chip's device register map. The DSP has its own sample RAM/ROM address spaces, DMA/DRQ interaction, 32 voice states, control/key-on semantics, interpolator, envelopes, filter arithmetic, 8-bit L/R gains, per-voice sends and ten routed output channels.

The MPC2000 driver connects the DSP at I/O addresses `0x0080..0x008f`, connects its DMA to channel 3, and configures `33.8688 MHz / 768 = 44.1 kHz`. The device's ten outputs are stereo main plus eight individual outs. Its sound-stream updater loops voices and frames.

**Extract *after* capturing the input event sequence and the DSP's complete behavior**, not by rewriting the mixer with new floating-point stages. The eventual GUI should emit register writes in the same order as the preserved input tape. ASIO/WAV callbacks only transport completed output, not define the DSP timebase.

## Trace tap map

| Event | Source | Captures | Caveat |
|---|---|---|---|
| `select` | `voice_select_w` | ordered register/voice selection, write mask, emulated chip tick | captures commands before mapping to voice/register |
| `register` | `voiceregs_w` | sequence, virtual tick/frame, voice, register, word, 48-bit shadow | order preserved |
| `atomic` | `atomic_w` | ordered atomic register clear | required for replay |
| `dma_request` / `dma_write` / `dma_read` / `dma_read_value` | DMA callbacks | sample memory transfer, addresses, values, chip-tick timing | dma_read and dma_read_value are paired; only DMA traffic via DSP is captured |
| `control` / `key_on` | `control_w` | control commands, frame, start/end/step | event frame is after `m_stream->update()` |
| `memory` | `read_sample` | every source RAM/ROM sample read and expanded PCM | one interpolated frame may read multiple samples |
| `interpolation` | `sound_stream_update` | address, 12-bit fraction, interpolator output | coefficients are MAME's approximate model |
| `filter` | `sound_stream_update` | envelope, cutoff, resonance, filter state/output | MAME model, not proven silicon widths |
| `voice_output` | `sound_stream_update` | 8-bit L/R gains, envelope, pre-mix L/R contribution | **not final summed output PCM** |
| `send` | `sound_stream_update` | channel mapping and per-voice send contribution | excludes unfinished delay effect |
| `mix_output` | `sound_stream_update` | all 10 post-voice-mix output channels, exact IEEE754 float32 bits | **MAME output representation**, not proof of original hardware accumulator |

Audio frames are counted from the L6028 stream's frame timeline; control commands and DMA also log a virtual time tick measured at the emulated L6028 clock frequency, plus a monotonic input-event sequence. The callback/render chunk size must not affect frame numbers or calculations. The trace is logged in MAME's existing log stream, prefixed `L6028_TAP`. The `select`/`register`/`control`/`atomic` events capture CPU-visible sound chip commands; they do not expose individual V53 CPU instructions. The upstream `src/mame/akai/mpc2000.cpp` driver actually declares an MPC2000XL ROM set and is marked `MACHINE_NOT_WORKING`, not a validated original MPC2000 boot. The driver's V53 clock, CPU DMA callbacks, sound DSP routing, panel controller and other peripherals remain untouched. Because MAME renders by voice (not by interleaved frame), trace lines need not be in frame order; compare by frame/voice/stage.

## Capture switch

The header defaults to `L6028_CAPTURE_TRACE=0`; normal builds compile out all taps and trace state. For diagnostic builds only, define `L6028_CAPTURE_TRACE=1` consistently for the device translation unit and its header (e.g., a compiler preprocessor definition). Run MAME with `-log` to collect the `L6028_TAP` lines. Trace output is intentionally verbose; use short deterministic stimuli. Diagnostic builds are **not suitable for performance benchmarking**.

## Validation gates

1. Build MAME's baseline revision and this branch with the trace disabled. Compare digital PCM plus state for the *same* input recording; expected exact equality.
2. Enable the trace and verify trace-on versus trace-off PCM equality. Do not assume logging is timing-neutral until verified with recorded register events.
3. Capture: register/control writes with timestamps, memory sample contents, DMA interactions, per-voice states, mixer contributions, and 10-channel MAME post-voice-mix stream output. Traces are now coded, but **capturing a real audio run is not yet validated**, and this does not capture every possible external device/CPU memory write or original silicon post-mix bits.
4. Replay the exact captured events into the untouched L6028 model. Verify frame-by-frame all 10 output channels, state and event ordering against the MAME reference.
5. Only then isolate the engine behind a host adapter for WAV, MIDI, GUI and ASIO.

### Known limitations

- The driver named `mpc2000.cpp` currently declares the **MPC2000XL** machine and is explicitly marked nonworking; the original MPC2000 is not separately proven by this driver. The MPC2000 MAME driver is not established here as a fully working instrument. A reference chip test driver or recorded register tape may be necessary before meaningful sound is produced.
- MAME's sinc coefficient table, interpolation boundary handling, filter arithmetic and some output precision are reconstructed; they are not proof of original Akai silicon behavior.
- Preserving the code does not guarantee the user's desired sonic presentation. The first listening test must use the same 16-sample multi-voice kit, with controlled levels and captured PCM.
- No DAC, analog circuitry, sequencer, new DSP algorithms, or The 48 modules are in scope.

## Next executable work

Add a focused deterministic L6028 chip harness: load signed 16-bit samples into the device address space; submit time-stamped register writes and key-on; pull 10 output channels for a fixed number of frames; write a repeatable digital reference fixture. Do this before GUI or VST3 work.

## Phase 2 interpretation and remaining blockers

- **Captured CPU boundary, not CPU instruction execution**: Voice-select, register-word writes, atomic resets, control commands and DMA events are the necessary sound-chip input protocol. CPU PC/instruction trace would be separately enabled only if a register sequence cannot be explained.
- **Sub-frame ordering**: `seq` is the total order of incoming events within the chip; `tick` uses the MAME machine's virtual time projected onto the L6028's own input-clock frequency. `frame` reflects the count of sample frames the device has rendered, not a guaranteed CPU instruction-cycle timestamp.
- **Output semantics**: The device uses `stream.add_int(..., 32768)`, which converts integer voice contributions into MAME's float32 output buffer. `mix_output f32bits` is an exact representation of those MAME samples after voice sums, before speaker routing. It is not verified bit-exact Akai digital output.
- **Required playback path**: A dedicated chip-level fixture must provide PCM RAM, a deterministic register-write tape and a reproducible stream render, then compare trace/no-trace and unmodified-reference results. Do not conclude anything about presentation until this fixture is producing and testing samples.
- **Legal**: no proprietary Akai ROMs are bundled; source code from the MAME fork retains its licensing.

## Listening/output inspection

When a trace-enabled MAME build has produced a real `error.log`, convert its *post-voice-mix MAME output* without changing any sample bit patterns:

```powershell
py scripts/l6028_tap_summary.py error.log
py scripts/test_l6028_capture_protocol.py
py scripts/test_l6028_trace_to_wav.py
py scripts/l6028_trace_to_wav.py error.log --output l6028-stereo-f32.wav
py scripts/l6028_trace_to_wav.py error.log --output l6028-all10-f32.wav --channels all
```

The WAV exporter is strict: each output frame must contain all ten channels, exactly once, with no missing frames. A failed or incomplete trace is **not** turned into invented silence. Exported WAV uses WAVE_FORMAT_IEEE_FLOAT and exact 32-bit patterns from `mix_output`. This is a diagnostic representation of MAME's mix buffer, *not a verified hardware DAC stream*. These commands do **not** produce sound until an actual MAME chip run or fixture has produced trace records.

## Supplied MPC2000XL firmware

Two user-supplied MPC2000XL OS revisions have been matched byte-for-byte against MAME's existing 1.14 and 1.20 ROM checksums. See [the private-firmware audit and local staging guide](FIRMWARE.md). Firmware bytes are deliberately **not** committed; the required 32 KiB panel-controller ROM remains missing. The currently defined MAME machine is **MPC2000XL**, not a verified original MPC2000.
