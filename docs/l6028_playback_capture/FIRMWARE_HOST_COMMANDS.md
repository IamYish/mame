# MPC2000XL L6028 host transaction handoff

Source: user-supplied static excavation of MPC2000XL firmware 1.14 (SHA1 f272ef2b1948730446fe260e4c0c830884832d3a) and 1.20 (SHA1 382be688972fe3d85caeca99abff4b6c391347fb), with original machine-code evidence addresses supplied in that report. These are research claims, not newly boot-traced or independently verified silicon behavior.

## Host-operation emitter

The ROM-free fixture now provides `emit_host()` operations: SELECT at 0x80, W0 at 0x82, W1 at 0x84, W2 at 0x86, ATOMIC at 0x8C, CONTROL at 0x88, and a distinct KEYON_RMW operation that reads the prior 0x88 control word, clears bit 7 and sets bit 8 before writing. Calls go directly to the *existing* L6028 host handlers. They do not alter DSP code or formulas.

**Default behavior is unchanged:** the original two-voice fixture and eight-sample fixture continue issuing their old W0→W1→W2 transaction order, fixed test registers, and fixed 0x0100 key-on. This preserves a known reference; it does NOT imply those values or this order are normal firmware behavior. RMW and ATOMIC are available for a later concrete firmware command sequence, but are not silently substituted now.

## Candidate changes, held until their preconditions are known

| Command or register | Static firmware evidence | Lab action |
|---|---|---|
| Start reg0 | W2→W1→W0; W2 OR 0x0100; descriptor +18h/+1Ah | HOLD until descriptor/address/type is known |
| End reg1 | W0 plus end descriptor +1Ch/+1Eh; conditional fallback if descriptor byte +7 equals 0 | HOLD branch and packed end unknown |
| Pitch reg1 | pitch table 0x57D06; index 0 gives 0x1000 | KEEP 0x1000 for nominal stimulus, not universal notes |
| Loop reg2 | conditional code and descriptor +20h/+22h/+24h/+26h | HOLD until branch resolved |
| Volume reg3 | selected register and atomic operation | HOLD; current MAME atomic probe demonstrates register-shadow versus live envelope difference |
| Volume target reg4 | descriptor +12h/+14h; later conditional fades | HOLD until program values and note state known |
| Filter reg5/6 | descriptor +28h/+2Ah/+2Ch/+2Eh and exponential lookup | HOLD; 7FFF/7FF0 test-only |
| Mixer reg7 | descriptor +0Ah/+0Bh left/right; +0Ch/+0Dh routing/send; output table | HOLD; FF/FF is test-only |
| Key-on | read-modify-write of control word 0x88 | emitter available, not used until state context validated |
| Key-off | later reg4 fade sequence rather than normal direct reg3 write | HOLD precise fade/timing and trigger condition |
| DMA/voice scheduling | V53 DMA, 32 voices, branch-specific host events | HOLD actual timing/descriptor context |

**Test gates:** output-to-output byte identity across equivalent legacy runs and tracing enabled/disabled, with pinned output hash checks. Input PCM and output PCM should NOT be made equal; natural differences are the object of study. The next valid experiment is one fully specified descriptor and mutually exclusive firmware branch that gives complete 16-bit host commands in order—not a fabricated replay of unresolved static templates.
