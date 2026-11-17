# L6028 eight-sample PCM pack (private local data)

The user's `samples 2.zip` contains exactly eight **44.1 kHz, signed 16-bit, mono WAVs**: kick, two closed hats, snare, clap, open hat, rim, and snap. These are real user audio assets and **are not committed into GitHub**.

A local packer `scripts/l6028_pack_wavs.py` validates each WAV without changing sample values, numbers it by its 1–8 filename prefix, and creates a little-endian PCM16 sample-memory image. Each voice receives a 32,768-word address slot at `0x1000 + 0x8000 * voice` with at least 16 zero guard samples after the end, ensuring the chip's address mask/alignment rules. A JSON manifest retains name, length, address and PCM SHA-256.

Usage (after checking out `lab/l6028-capture`):

```powershell
py scripts/l6028_pack_wavs.py "C:\path\samples 2.zip" --output "C:\path\l6028_samples.bin" --manifest "C:\path\l6028_samples.json"
$env:L6028_SAMPLE_PACK = "C:\path\l6028_samples.bin"
.\l6028lab.exe l6028lab -log -nothrottle -video none -sound sdl -samplerate 44100 -wavwrite eight-sample-PCM16.wav
```

Build the ROM-free MAME `l6028lab` subtarget using the documented MAME MSYS2 toolchain. On Linux, specify `L6028_SAMPLE_PACK=/path/l6028_samples.bin` with the executable; locate the output binary according to the build.

## Event service

Each of the eight distinct source WAVs is triggered 4,410 internal L6028 frames (100 ms) apart using an emulated-time timer. A separate note-off register write at the source's original frame length prevents unwanted repeated loops, and exits 2,048 frames after the last note-off. Each trigger and stop uses exactly the chip's original register interface via `lab_host_w`, and never replaces L6028 interpolation, filtering, envelope or mix arithmetic. The event timer jumps between consequential deadlines; it does not dispatch one host operation per machine edge.

With no `L6028_SAMPLE_PACK` environment variable the original two-voice fixture is retained identically. With an invalid path or malformed pack, the test explicitly fails instead of substituting synthetic sound.

## Test limits

- This phase proves **8 mono WAVs** pass through the intact reconstructed L6028 device; the previously agreed **16 stereo-sample listening test** is a separate later gate.
- The output WAV is MAME's **speaker-side PCM16**, not a verified silicon DAC-latch bitstream.
- The public CI synthesizes eight harmless PCM16 WAVs and runs the same packer and eight-voice playback mode using a trace-disabled build. The user's original sample data never enters CI.
- New pack-mode source and CI are not considered functioning until the actual MAME compilation and execution pass.
