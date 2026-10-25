# Working on gitSynth (notes for AI assistants)

gitSynth is a REAPER JSFX guitar synthesizer. Read [README.md](README.md) for the layout and tools, [PLAN.md](PLAN.md) for design and status, and [jsfx/lib/README.md](jsfx/lib/README.md) before touching or reusing a library.

## Rules

- **Sliders:**
  - Give every slider a variable name (`slider13:swell_ms=...`) and use only the name in code.
  - Group sliders logically, and leave a free number after each group.
  - Stay within 64 sliders.
  - Never renumber existing sliders without converting saved presets. Presets store values by slider number.
- **No custom `@gfx`:** every control must be reachable as a slider, because the plugins are used with a screen reader. Report status by writing to read-only sliders.
- **Libraries in `jsfx/lib`:**
  - Follow the conventions in its README: cookDSP object style, `gs_` prefix, `memalloc` only in `_init`, no globals.
  - Every plugin's `@init` starts with `__memory_next = 0;`.
- **Measure, don't assume:**
  - Check changes by rendering the real JSFX with `tools/render.py` and the measurement tools. Python copies of the DSP are for exploring only.
  - REAPER must be closed to render. If it's open, ask the user to close it rather than working around it.
- **Physical models:** test with the noise switched off after the note starts. A noise-fed loop shows a "pitch" without oscillating.
- **Pitch measurements:** the pYIN reference starts notes about 50 ms early. Measure from the pick (`compare_pitch.pick_times`).
- **Git:** local operations only. Never push or touch remotes.

## Useful facts

- **JSFX:**
  - EEL2 names are case-insensitive.
  - cookDSP defines `onset`, `delay`, `random`, `gate`, `tanh` and others; avoid those names.
  - cookDSP's `tanh` overflows on large inputs; use a guarded version.
- **Rendering:**
  - Project and render rate must be forced to 48 kHz (`SAMPLERATE 48000 1 0`).
  - Renders include a 1-second tail.
  - Batch renders use stems with the pattern `$track`. REAPER also writes `Master.wav`, which the tools delete.
- **Pitch tracking:**
  - Clean notes have an aperiodicity below 0.05.
  - Pick noise lasts about 3 to 4 ms on the high strings.
  - The tracker locks 6 to 16 ms after the pick.
