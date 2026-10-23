# gitSynth: Plan and Spec, Version 1

A real-time guitar-to-flute synthesizer for REAPER, written in JSFX. It uses the guitar's own audio, with no MIDI and no samples.

## Decisions from the interview

- Input: a normal guitar on one mono cable, with no hex pickup.
- Polyphony: monophonic. Clean single-line tracking is the priority. Chords are left for a later version.
- Language: JSFX. Rust/CLAP and Faust are set aside for now.
- Voice: a flute, or a resonant tube.
- Volume: follows the guitar's natural envelope by default, with a "hold" option.
- Use: live playing, so there is no lookahead.
- Range: standard tuning, from low E (82.4 Hz) up to about the 24th fret on high E (about 1.3 kHz).
- Pitch: a choice between following exactly and snapping to the nearest semitone, with a snap-strength and a glide slider.
- Testing: Rich records clean direct-input (DI) clips. These are used for offline measurements.

## Acceptance targets

- No octave jumps on held notes, including on the low E and A strings.
- The pitch locks within about 2 periods of the fundamental. That is about 25 ms on low E and under 5 ms on high notes. The breath and attack hide the gap.
- Bends and vibrato are followed smoothly, with no stepping and no warble.
- A muted string stops the note, with no stray pitches during the decay.
- Hammer-ons, pull-offs and slides retune the note without restarting the envelope.
- CPU use stays low enough that one instance is a small fraction of one core at 48 kHz with a 64-sample buffer.

## Architecture

The signal passes through these stages in order:

1. Input conditioning: remove DC offset and high-pass the signal at about 70 Hz.
2. Envelope follower and gate: measure loudness, and decide note-on and note-off with hysteresis.
3. Onset detector: spot new pick attacks so the tracker can reset quickly.
4. Coarse pitch estimate (YIN): decimate the signal by 4 to 12 kHz and run YIN on the result. YIN is a standard single-note pitch algorithm based on a difference function. It runs every 16 decimated samples, and parabolic interpolation adds sub-sample precision.
5. Fine tracking (PLL): run a numerically controlled oscillator at the full sample rate. Its starting value comes from YIN at each onset. After that it is locked to the zero crossings of the fundamental, isolated with a band-pass filter that follows the tracked pitch. A lock detector reports when the pitch can be trusted.
6. Note logic: guard against octave errors, detect legato (a pitch change without an onset), and detect muting.
7. Pitch shaping: choose follow or snap mode, apply snap strength, then glide.
8. Voice: produce the flute sound (see below).
9. Attack masking: let a little of the guitar's own attack through until the PLL locks, then crossfade to the voice.
10. Output: dry/wet mix and output level.

### Why decimate before YIN

- Running YIN at 48 kHz for low E costs about 680,000 multiplies per update. Updating that often is too slow in EEL2, the JSFX scripting language.
- At 12 kHz the same search is about 21,000 multiplies per update, which is cheap even at 750 updates a second.
- The anti-alias filter adds about 1 ms of delay. The PLL runs at the full rate, so no fine precision is lost.

### Voices

- Voice A, imitation flute (build first):
  - A sine wave, plus small 2nd and 3rd harmonics.
  - Breath noise through a band-pass filter tuned to the note, with its level following picking strength.
  - A noise "chiff" at each onset.
  - Vibrato that can be delayed after the note starts.
  - This voice is always in tune, so it shows exactly what the tracker is doing.
- Voice B, waveguide tube (build later):
  - The STK-style flute model: a bore delay line with fractional-delay tuning, a jet delay, a cubic nonlinearity, and breath pressure plus noise as the excitation.
  - It is more realistic, but it shows up tracking errors more and can become unstable.

### Controls (sliders only)

- Pitch mode: Follow or Snap.
- Snap strength: 0 to 100%.
- Glide time: in ms.
- Envelope mode: Follow guitar, or Hold.
- Breath noise amount.
- Chiff amount.
- Vibrato depth, rate and delay.
- Brightness: the harmonic mix.
- Attack masking amount.
- Gate threshold.
- Dry/wet mix.
- Output level.
- Status (read-only): the detected note and lock state, written back by the code so a screen reader can read it in REAPER's parameter list. This is optional.

There is no custom `@gfx` window. Every control appears in REAPER's standard FX parameter list, so the screen reader can reach all of them.

## Testing method

- Test clips go in `clips/`. The exact recording requirements are in [RECORDING.md](RECORDING.md): format, signal path, levels, file names, and what to play in each clip.
- Several clips have a fixed, known note order, such as the chromatic and open-string clips. This means the reference tracker can also be checked against the notes that were actually played.
- The reference pitch comes from an offline high-accuracy tracker, pYIN in Python's librosa, run on the same clips.
- A debug build of the JSFX writes the tracked pitch and lock state to extra output channels.
- REAPER renders the clips from the command line (`reaper.exe -renderproject`).
- A Python script compares the rendered pitch channel with the reference. It reports octave errors, lock time per note, pitch jitter in cents, and stray notes during muting.
- An alternative to check: ysfx, a library that runs JSFX outside REAPER. It may allow testing without REAPER.
- Every tracker change is run against the clips, and the numbers are kept, so regressions are caught.

## Build steps

Each step is small and can be undone on its own.

0. Set up: create a local git repository, the folder layout, a `clips/` folder, and the Python reference-pitch script (`tools/reference_pitch.py`).
1. Coarse tracker only: conditioning, gate, onset detection, decimation and YIN. The output is a plain sine at the tracked pitch, plus debug channels. Measure the results.
2. Add the PLL: seed it from YIN, lock to the fundamental's zero crossings, and add the lock detector. Measure jitter and how well bends are followed.
3. Note logic: the octave guard, legato detection and mute detection. Measure.
4. Voice A with all controls, including the pitch modes and the envelope modes.
5. Attack masking.
6. Voice B, the waveguide tube.
7. Later and optional: a lookahead mode for recorded tracks, a polyphonic filter-bank mode for chords, and a port to Rust as a CLAP plugin.

## Known limitations

- On low E there is about 25 ms of pitch-lock delay that physics does not allow us to remove. It is masked, not eliminated.
- Chords are not supported. A chord will make the tracker lock onto one note, or jump between notes.
- Heavily distorted input will track badly. Feed the plugin the clean DI signal and put effects after it.
- JSFX runs on one thread with no SIMD. That is fine for one mono voice, but it limits future polyphonic work in JSFX.
- The plugin runs only in REAPER.
