# Native WAV capture coverage

The original ON/OFF native WAVs are bit-identical (SHA-256 `13931d2e4caea2cd1b20b68da96374d95f174870d7995db27e0da7442b9e2ccd`) but cover **only 1765 frames** versus the **2269** post-voice-mix frames in the full chip reference. That is incomplete host comparison coverage.

In the new dedicated MAME WAV capture jobs, `L6028_NATIVE_FLUSH=1` stops the two voices at the existing final deadline through the original L6028 register handlers, then allows another **4096** virtual audio frames for MAME's speaker recorder to flush. Without the environment variable the original fixture, existing 2269-frame PCM reference, and event timeline stay unchanged.

The new gate rejects recordings with fewer than 2269 frames and requires the trace-on and trace-off native WAVs to match byte for byte. This checks the full short stimulus at the speaker-side output, not all original silicon state or DAC behavior. Not yet verified by CI at the time of this source commit.
