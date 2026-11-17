# Atomic register-3 probe: current emulator behavior, not silicon proof

The MPC2000XL firmware excavation identified select-register-3 followed by an atomic write to port 0x8C; our previous two-voice fixture instead wrote a 0xFFFF envelope directly.

An opt-in isolated MAME diagnostic (L6028_ATOMIC_PROBE=1) writes an **arbitrary** 0x2000 test value into reg3 W1, reads it, issues the real atomic handler, reads W1 again, then writes regular W1=0 and reads once more. It does not trigger any sample.

The current MAME source clears the selected raw register on atomic writes, but does not explicitly change the live env_volume. A read of reg3 W1 mirrors the live envelope into the register shadow. A regular W1 write does update env_volume.

Expected *MAME model* observation: L6028_ATOMIC_PROBE_RESULT before=2000 after_atomic=2000 after_regular=0000

This is a source-derived regression expectation, not a recovered Akai default, confirmation of real silicon semantics, or permission to correct output PCM.

Implementation changes: one read adapter through existing voiceregs_r/control_r handlers, an opt-in ROM-free probe, a CI log assertion. No DSP arithmetic, interpolation, envelopes, gain, mixer, clocks or default two-voice/8-sample host commands are modified.

Follow-up: obtain a concrete firmware/program descriptor so we can replay the true note initialization command tape (including register order and branch choice) rather than fabricate missing values.
