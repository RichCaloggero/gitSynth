# gitSynth: Plan and Spec, Version 1

A real-time guitar synthesizer for REAPER, written in JSFX. It uses the guitar's own audio, with no MIDI and no samples. It has two parts, built in this order:

- Part 1, processed guitar: the string's own sound, reshaped with envelopes, filters and waveshaping. It needs no pitch tracking, still sounds plucked, and handles chords.
- Part 2, tracked voice: oscillators driven by the pitch of the string. It needs pitch tracking and plays one note at a time.

A mix control blends the two, much like the two kinds of sound in the Boss SY-1000.

## Decisions from the interview

- Input: a normal guitar on one mono cable, with no hex pickup.
- Target sound: a plucked string that can then be shaped. It does not need to sound like a flute.
- Build order: Part 1 first, then Part 2 (decided 2026-10-23).
- Polyphony: Part 1 handles chords, except its square-up and octave stages, which need single notes. Part 2 is monophonic, and clean single-line tracking is its priority.
- Language: JSFX. Rust/CLAP and Faust are set aside for now.
- Volume: follows the guitar's natural envelope by default, with a "hold" option.
- Use: live playing, so there is no lookahead.
- Range: standard tuning, from low E (82.4 Hz) up to about the 24th fret on high E (about 1.3 kHz).
- Pitch (Part 2): a choice between following exactly and snapping to the nearest semitone, with a snap-strength and a glide slider.
- Testing: Rich records clean direct-input (DI) clips. These are used for offline measurements.

## Acceptance targets

### Part 1

- No added latency: every stage works sample by sample.
- Chords stay clean at low waveshaping settings.
- No clicks or zipper noise when sliders move or the filter sweeps fast.
- CPU use is negligible: well under one percent of a core.

### Part 2

- No octave jumps on held notes, including on the low E and A strings.
- The pitch locks within about 2 periods of the fundamental. That is about 25 ms on low E and under 5 ms on high notes. The attack hides the gap.
- Bends and vibrato are followed smoothly, with no stepping and no warble.
- A muted string stops the note, with no stray pitches during the decay.
- Hammer-ons, pull-offs and slides retune the note without restarting the envelope.
- CPU use stays low enough that one instance is a small fraction of one core at 48 kHz with a 64-sample buffer.

## Part 1 architecture: processed guitar

The signal passes through these stages in order:

1. Input conditioning: remove DC offset and high-pass the signal at about 70 Hz.
2. Envelope follower: measure picking strength and loudness. It drives the later stages.
3. Envelope reshaping:
   - Attack softening or a slow swell, which removes the pick click.
   - Sustain: a compressor that holds the note up as the string decays. The "hold" option lives here.
4. Waveshaper: soft clipping or wave folding, to add or change harmonics. The amount is low by default, so chords stay clean.
5. Envelope-controlled resonant filter: a low-pass filter (a state-variable filter) whose cutoff sweeps with picking strength. Its controls are base cutoff, sweep depth and direction, sweep speed, and resonance.
6. Body resonance: a few fixed band-pass peaks shaped like the response of a violin or cello body, so the sound seems to come from a wooden instrument. It works on chords.
7. Frequency-shifter ensemble: it shifts every harmonic by the same few Hz, using a Hilbert transform built from all-pass filters, so it adds no latency. Two copies shifted in opposite directions spread one guitar into a section-like sound. Its range is limited to a few Hz, because larger shifts destroy the sound.
8. Vibrato: a short delay line whose delay time wobbles, which bends every note of a chord together. It can start after a delay once the note has swelled in, timed from the swell stage.
9. Dynamic freeze: dropped 2026-10-23. Hold already gives clean, near-endless sustain, and an attack-released freeze added little beyond it. A manually triggered, layered freeze (a pad that holds while live playing continues on top) would be distinct, but needs a MIDI foot trigger; reconsider if one is available. The last version is in git history (commit d8d2a55).
10. Vowel filter: two or three band-pass filters at the formants of a vowel. The envelope moves them between two chosen vowels, for "wah-ow" and talk-box-like sounds. It works on chords.
11. Resonator bank: tuned comb filters set to fixed notes, chosen as a root note plus a chord or scale. The guitar makes them ring, for a sitar-like or drone shimmer.
12. Square-up and octave-down, optional, single notes only: a comparator with hysteresis makes a square wave at the string's frequency. A flip-flop halves it to one octave below, and the result is shaped by the guitar's envelope. It feeds the filter in parallel with the guitar and has its own mix level. There is no octave-up stage; Rich finds it too metallic.
13. Output: dry/wet mix and output level.

Part 1 centres on chord-friendly processing of the swelled, violin-like sound (decided 2026-10-23). The square wave is optional. The order of stages 9 to 11 is provisional and may change once they can be heard.

Later options, if wanted: a phaser, and a second filter.

### Part 1 controls (sliders only)

- Attack (swell) time.
- Sustain amount.
- Drive and shape for the waveshaper.
- Filter base cutoff, sweep depth, sweep direction, sweep speed and resonance.
- Body resonance: body type (violin, viola or cello), amount.
- Ensemble: shift amount in Hz (a small range), number of copies and mix.
- Vibrato: depth, rate, onset delay and fade-in time.
- Vowel filter: start vowel, end vowel, sweep amount and mix.
- Resonator bank: root note, chord or scale, decay time, brightness and mix.
- Square wave level and octave-down level.
- Envelope mode: Follow guitar, or Hold.
- Dry/wet mix.
- Output level.

## Part 2 architecture: tracked voice

The signal passes through these stages in order:

1. Input conditioning: shared with Part 1.
2. Envelope follower and gate: measure loudness, and decide note-on and note-off with hysteresis.
3. Onset detector: spot new pick attacks so the tracker can reset quickly.
4. Coarse pitch estimate (YIN): decimate the signal by 4 to 12 kHz and run YIN on the result. YIN is a standard single-note pitch algorithm based on a difference function. It runs every 16 decimated samples, and parabolic interpolation adds sub-sample precision.
5. Fine tracking (PLL): run a numerically controlled oscillator at the full sample rate. Its starting value comes from YIN at each onset. After that it is locked to the zero crossings of the fundamental, isolated with a band-pass filter that follows the tracked pitch. A lock detector reports when the pitch can be trusted.
6. Note logic: guard against octave errors, detect legato (a pitch change without an onset), and detect muting.
7. Pitch shaping: choose follow or snap mode, apply snap strength, then glide.
8. Voice: produce the synth sound (see below).
9. Attack masking: let a little of the guitar's own attack through until the PLL locks, then crossfade to the voice.
10. Output: mix with Part 1, then output level.

### Why decimate before YIN

- Running YIN at 48 kHz for low E costs about 680,000 multiplies per update. Updating that often is too slow in EEL2, the JSFX scripting language.
- At 12 kHz the same search is about 21,000 multiplies per update, which is cheap even at 750 updates a second.
- The anti-alias filter adds about 1 ms of delay. The PLL runs at the full rate, so no fine precision is lost.

### Voices

- Voice A, simple oscillators (build first):
  - Sine, saw or square waves at the tracked pitch, with a brightness control, then the same kind of filter as Part 1.
  - An optional breath noise through a band-pass filter tuned to the note, which gives a flute-like colour.
  - Vibrato that can be delayed after the note starts.
  - This voice is always in tune, so it shows exactly what the tracker is doing.
- Voice B, waveguide tube (build later):
  - The STK-style flute model: a bore delay line with fractional-delay tuning, a jet delay, a cubic nonlinearity, and breath pressure plus noise as the excitation.
  - It is more realistic, but it shows up tracking errors more and can become unstable.

### Part 2 controls (sliders only)

- Pitch mode: Follow or Snap.
- Snap strength: 0 to 100%.
- Glide time: in ms.
- Waveform and brightness.
- Breath noise amount.
- Vibrato depth, rate and delay.
- Attack masking amount.
- Gate threshold.
- Part 1 / Part 2 mix.
- Status (read-only): the detected note and lock state, written back by the code so a screen reader can read it in REAPER's parameter list. This is optional.

There is no custom `@gfx` window in either part. Every control appears in REAPER's standard FX parameter list, so the screen reader can reach all of them.

## Testing method

- Test clips go in `clips/`. The exact recording requirements are in [RECORDING.md](RECORDING.md): format, signal path, levels, file names, and what to play in each clip.
- Part 1 is judged mainly by ear, live and on the clips. A render of the clips also checks for clipping, clicks and added latency.
- For Part 2:
  - Several clips have a fixed, known note order, such as the chromatic and open-string clips. This means the reference tracker can also be checked against the notes that were actually played.
  - The reference pitch comes from `tools/reference_pitch.py`: pYIN in Python's librosa finds the notes, and YIN measures their precise pitch.
  - A debug build of the JSFX writes the tracked pitch and lock state to extra output channels.
  - REAPER renders the clips from the command line (`reaper.exe -renderproject`).
  - A Python script compares the rendered pitch channel with the reference. It reports octave errors, lock time per note, pitch jitter in cents, and stray notes during muting.
  - An alternative to check: ysfx, a library that runs JSFX outside REAPER. It may allow testing without REAPER.
  - Every tracker change is run against the clips, and the numbers are kept, so regressions are caught.

## Build steps

Each step is small and can be undone on its own.

0. Set up: a local git repository, the folder layout, a `clips/` folder, and the Python reference-pitch script (`tools/reference_pitch.py`). Done 2026-10-23.

Part 1, processed guitar:

1. Skeleton and filter: input conditioning, the envelope follower, the envelope-controlled resonant filter, dry/wet and output level. Done 2026-10-23.
2. Envelope reshaping: attack softening or swell, sustain, and the Hold mode. Done 2026-10-23.
3. Waveshaper. Done 2026-10-23.
4. Body resonance. Done 2026-10-23.
5. Frequency-shifter ensemble. Done 2026-10-23. Then moved into a shared library (`jsfx/gitsynth/freqshift.jsfx-inc`) with an LFO (sine, triangle, random step, random smooth) that wobbles each copy's shift, and also released as a standalone effect, `jsfx/gitSynth-freqshift.jsfx`.
6. Vibrato with delayed onset. Done 2026-10-23. Shared library `jsfx/gitsynth/vibrato.jsfx-inc`; shapes refer to the pitch heard (sine, triangle, random step, random smooth). A simple attack detector times the onset; step 7 will reuse and refine it.
7. Dynamic freeze: dropped 2026-10-23 (see stage 9 above). The attack threshold slider it added stays, for the vibrato onset.
8. Vowel filter. Shared library `jsfx/gitsynth/vowel.jsfx-inc`: three formant band-passes, moved by the main sweep amount, with a slow level match.
9. Resonator bank.
10. Optional: square-up and octave-down.

Part 2, tracked voice:

11. First set up a test rig that runs the real JSFX on the clips: REAPER command-line render first, ysfx if that proves awkward. Until then, Part 1 is checked with Python ports and by ear (decided 2026-10-23). Then the coarse tracker only: gate, decimation and YIN, reusing the onset detector from step 7. The output is a plain sine at the tracked pitch, plus debug channels. Measure the results.
12. Optional spin-off: an accessible tuner JSFX built on the coarse tracker. It reports the note and cents through readable sliders and an audio cue.
13. Add the PLL: seed it from YIN, lock to the fundamental's zero crossings, and add the lock detector. Measure jitter and how well bends are followed.
14. Note logic: the octave guard, legato detection and mute detection. Measure.
15. Voice A with all controls, including the pitch modes, and the Part 1 / Part 2 mix.
16. Attack masking.
17. Voice B, the waveguide tube.
18. Later and optional: a lookahead mode for recorded tracks, a polyphonic filter-bank mode for chords, and a port to Rust as a CLAP plugin.

## Known limitations

- Part 1 cannot change the note's pitch or remove the guitar's character entirely. It shapes the string's sound but does not replace it.
- Part 1's square-up and octave stages glitch on chords and can misfire on strong harmonics.
- The resonator bank rings at fixed notes, so it suits playing in one key and clashes outside that key.
- On low E, Part 2 has about 25 ms of pitch-lock delay that physics does not allow us to remove. It is masked, not eliminated.
- Part 2 does not support chords. A chord will make the tracker lock onto one note, or jump between notes.
- Heavily distorted input will track badly. Feed the plugin the clean DI signal and put effects after it.
- JSFX runs on one thread with no SIMD. That is fine for one mono voice, but it limits future polyphonic work in JSFX.
- The plugin runs only in REAPER.
