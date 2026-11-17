# L6028 reconstructed PCM reference — Fixture 001

## Reference identity

- Source tree: `IamYish/mame`, pinned upstream foundation `19b605cf64f8d8ee10b169f49cb774b0efe46ddd`.
- Test branch: `lab/l6028-capture`; proven build commit `c4c3a4d70af174f0c587958be065b68b4965374c`.
- [Successful MAME test, run 44091818481](https://github.com/IamYish/mame/actions/runs/44091818481).
- [Download recorded MAME PCM and complete trace from Actions](https://github.com/IamYish/mame/actions/runs/44091818481/artifacts/14333031523).
- This report is based on the **actual downloaded binary WAVs and error.log**, not only CI exit status.

## Observations

| Observable | Result |
|---|---|
| Original MAME L7A1045 DSP compilation, linking and execution | PASSED |
| L6028 modeled clock and stream sample rate | 33.8688 MHz / 768 = 44.1 kHz |
| 16-bit stimulus playback | Two distinct integer-generated patterns |
| Key-on | Voice 0 at stream frame **1**; voice 1 at stream frame **221** |
| Key-on spacing | **220** internal audio frames |
| Stereo MAME post-voice-mix output | 2269 frames × 2 channels (51.451247 ms) |
| All MAME post-voice-mix outputs | 2269 frames × 10 channels |
| Voice 0 nonzero pre-mix contributions | **2268** of 2268 processed frames |
| Voice 1 nonzero pre-mix contributions | **2048** of 2048 processed frames |
| Main channel peak magnitude | **0.77340698** |
| Main channel RMS | **0.27653534** |
| Main stereo L/R relationship | Bitwise identical, by construction of test gains |
| Individual outputs 0–7 | All silent, because no sends are programmed |
| Source reads / interpolation / filter / voice-output trace entries | 4316 each |
| Output records | 22690 = 2269 frames × 10 channels |
| Main-sample quantization | Every output sample on an exact multiple-of-1/32768 grid in this short fixture |

### Content SHA-256 fingerprints (raw IEEE float32 PCM data bytes, not WAV headers)

```text
stereo: 1af54297681e9a22cb8fd7278693ade8c688bb79b5c7663bec296785db7c962c
all10:  aed4da3b2989afe3d34a9d4ac95117f737bb44e8615edc7dfde697d9580cac3b
```

### WAV file SHA-256 fingerprints (full RIFF bytes)

```text
main-f32.wav:  eff76df009ae768f731641e4d37d8961b70d84d49472d7b13f7f576285f43d6f
all10-f32.wav: 078a02bc94306b0bf4cb1f667e382a0e76ad7909fcf1fef08e685434e7f24ae3
```

The output WAVs use IEEE754 float32 MAME stream representation. The fixed 1/32768 grid is consistent with the implementation adding integer voice contributions scaled by 32768, and **does not establish that Akai silicon mixed in 16-bit or float32**.

### Engineering gates NOT yet established

1. Trace-on versus trace-off reference output equivalence: **not yet tested**.
2. Repeated independent executions producing byte-identical PCM: **new CI gate in progress**.
3. Digital output matching measured MPC2000 or MPC2000XL hardware: **not measured**.
4. Audible multi-sample presentation across a full 16 stereo sample kit: **not yet tested**.

The recording is **only ~51 ms** and uses synthesized test patterns. It is a reproducible machine execution proof, not a listening demonstration. Original MPC firmware and panel ROM are unnecessary for this chip-level experiment. This document contains no proprietary firmware.
