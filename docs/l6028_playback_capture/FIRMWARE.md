# MPC2000XL supplied firmware — verified identity, private usage

## What was added to the project

The user supplied two files. **Do not upload their proprietary ROM contents into this public GitHub fork.** Their cryptographic fingerprints match two distinct entries in the pinned MAME \`src/mame/akai/mpc2000.cpp\` ROM manifest:

| Private source | Inside archive | MAME required filename | BIOS | Size | CRC32 | SHA-1 |
|---|---|---|---|---:|---|---|
| \`MPC2KXL.BIN\` | — | \`mpc2000xl_114.bin\` | \`ver114\` | 524288 | \`7b4fe8af\` | \`f272ef2b1948730446fe260e4c0c830884832d3a\` |
| \`mpc2kxl.zip\` | \`MPC2KXL.BIN\` | \`mpc2000xl_120.bin\` | \`default\` | 524288 | \`c082f188\` | \`382be688972fe3d85caeca99abff4b6c391347fb\` |

The different checksums are **expected**: one is OS v1.14, the other OS v1.20. Identity was checked on the original bytes, not guessed from filename or filename case.

The MAME MPC2000XL driver **also requires** the separate 32768-byte \`akai mpc2000xl op v1_0.bin\` uPD78C10 panel-controller ROM (CRC32 \`24382ade\`, SHA-1 \`b02ca9b8a4ae41f4414e12d5188f638dbb99f36c\`). It was **not** contained in either supplied artifact. The ROMs do **not** make this MAME machine operational on their own; the driver declares \`MACHINE_NOT_WORKING\`.

The source file is called \`mpc2000.cpp\`, but it currently declares the **MPC2000XL** machine only. Its firmware will not establish the original non-XL MPC2000's OS behavior.

## Prepare on the Windows development machine

With the GitHub branch checked out locally, use the audit tool against the user's locally saved firmware files (it matches by *content*, including files inside ZIPs):

\`\`\`powershell
py scripts/mpc2000xl_rom_audit.py "C:\path\MPC2KXL.BIN" "C:\path\mpc2kxl.zip"
py scripts/mpc2000xl_rom_audit.py "C:\path\MPC2KXL.BIN" "C:\path\mpc2kxl.zip" --json
py scripts/test_mpc2000xl_rom_audit.py
\`\`\`

When the matching **panel controller ROM is legitimately available locally**, the full ROM ZIP can be made without sharing the firmware:

\`\`\`powershell
py scripts/mpc2000xl_rom_audit.py "C:\path\MPC2KXL.BIN" "C:\path\mpc2kxl.zip" "C:\path\PANEL.ROM" --stage "local-roms\mpc2000xl.zip"
\`\`\`

\`local-roms/\` is ignored by MAME's existing root \`.gitignore\` wildcard. Verify with \`git status\` before making any commit and never force-add the ROMs.

With a MAME executable from the **same source revision**, you can then try a ROM audit and the two BIOS selectors:

\`\`\`powershell
.\mame.exe -rompath local-roms -verifyroms mpc2000xl
.\mame.exe -rompath local-roms mpc2000xl -bios default -log
.\mame.exe -rompath local-roms mpc2000xl -bios ver114 -log
\`\`\`

A failed boot does **not** invalidate the firmware: check panel ROM, emulator completeness, errors from storage peripherals and CPU/DSP boundary traces separately. No resulting audio, working boot, or performance is claimed here.

## Research next step

1. Keep the complete MAME V53/panel/DMA/IRQ implementation as the reference.
2. If the machine boots far enough, capture initial CPU-to-L6028 register sequences using existing \`select\`, \`register\`, \`atomic\`, \`control\`, \`dma\` traces and the existing \`mix_output\` tap.
3. If firmware boot remains blocked, use the L6028 **chip-level sample-memory + register-tape test harness** rather than inventing new playback math.
4. Use a proven register tape to drive the same playback engine from our own GUI and MIDI. Track internal PCM and audio separately from any undocumented silicon assumptions.

This is an evidence-first firmware integration; it is **not** an MPC2000XL clone and not a claim of reproducing the original MPC2000's sonic presentation.
