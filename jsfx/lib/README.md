# gitSynth JSFX libraries

Reusable DSP building blocks for REAPER JSFX, written for gitSynth but usable in any JSFX. Each file is one `.jsfx-inc` library holding one or more objects.

## Contents

- [What is here](#what-is-here)
- [Requirements](#requirements)
- [Using a library](#using-a-library)
- [Conventions](#conventions)
- [Library reference](#library-reference)
- [Pitfalls](#pitfalls)
- [Performance](#performance)
- [Adding a library](#adding-a-library)
- [Testing](#testing)
- [Credits](#credits)

## What is here

| File | Objects | What it does |
|---|---|---|
| `freqshift.jsfx-inc` | `gs_hilbert`, `gs_shift`, `gs_lfo`, `gs_ensemble` | 90-degree phase splitter, frequency shifter, LFO with four shapes, and a chorus-like ensemble built from them |
| `vibrato.jsfx-inc` | `gs_vibrato` | Stereo delay-line vibrato whose shapes describe the pitch heard |
| `vowel.jsfx-inc` | `gs_vowel` | Three-formant vowel filter with level matching |
| `tracker.jsfx-inc` | `gs_tracker`, `gs_pll` | Monophonic pitch tracker (YIN on a decimated signal), plus an experimental fine tracker |
| `flute.jsfx-inc` | `gs_flute` | Waveguide flute physical model with breath noise |

## Requirements

- REAPER 7 or later. Older versions should work but are untested.
- [cookDSP](../cookdsp/) by Olivier Bélanger, which is in this repository. Every library uses its `memalloc`, and `vibrato` also uses its `delay` object.
- Sample rate: tested at 48 kHz. Everything is computed from `srate`, but tunings and measurements in the comments are for 48 kHz.

## Using a library

1. Put this `lib` folder and the `cookdsp` folder side by side, next to your plugin:

   ```
   MyPlugin.jsfx
   cookdsp/cookdsp.jsfx-inc
   cookdsp/cookdsp/...
   lib/freqshift.jsfx-inc
   ```

2. Import cookDSP first, then the libraries you need. JSFX resolves `import` relative to the importing file:

   ```
   import cookdsp/cookdsp.jsfx-inc
   import lib/freqshift.jsfx-inc
   ```

3. In `@init`, reset cookDSP's memory allocator **before** creating any object, then create each object once:

   ```
   @init
   __memory_next = 0;     // memalloc starts again on every re-init
   ens.gs_ensemble_init();
   ```

   `@init` runs again whenever the sample rate changes or playback restarts. Without the reset, every re-init allocates fresh memory, and memory use grows each time.

4. Call the object's `_do` function once per sample in `@sample`, and read its results:

   ```
   @sample
   ens.gs_ensemble_do(spl0, 1, 1, 0.5, 1, 0.3, 0.2, 3);
   spl0 = ens.l;
   spl1 = ens.r;
   ```

### A complete example

A stereo chorus plugin built from the ensemble object, with every control as a named slider:

```
desc:Example ensemble chorus

slider1:shift_hz=1<0.05,10,0.05:log>Shift (Hz)
slider2:mix_pct=50<0,100,1>Mix (%)
slider3:spread_pct=100<0,100,1>Stereo spread (%)

import cookdsp/cookdsp.jsfx-inc
import lib/freqshift.jsfx-inc

in_pin:Left
in_pin:Right
out_pin:Left
out_pin:Right

@init
__memory_next = 0;
ens.gs_ensemble_init();

@sample
m = 0.5 * (spl0 + spl1);
ens.gs_ensemble_do(m, shift_hz, 1, mix_pct / 100, spread_pct / 100, 0.3, 0.2, 3);
spl0 += ens.l - m;
spl1 += ens.r - m;
```

`jsfx/gitSynth-freqshift.jsfx` is the full version of this.

## Conventions

- **Objects in cookDSP's style:** each object is used through a variable name as prefix, for example `ens.gs_ensemble_init()`. Inside the functions, `this.` refers to that object's own variables, so you can have as many independent copies as you like: `a.gs_vowel_init(); b.gs_vowel_init();`.
- **Two calls per object:**
  - `name_init(...)` goes in `@init`.
  - `name_do(...)` goes in `@sample`, once per sample. It returns the result, or sets fields such as `this.l` and `this.r`, as each object's reference below says.
- **Names:**
  - Every function starts with `gs_`, so nothing clashes with cookDSP or with your own code.
  - Constants are `GS_<LIBRARY>_<NAME>` in capitals, defined in the library's `@init`.
- **No globals:** libraries only use their parameters, their own `this.` variables and their constants. They never read your sliders or your variables.
- **Units:**
  - Frequencies are in Hz.
  - Times in parameters are in the units the name says, usually ms or s.
  - Amounts named `mix`, `depth` or `gain` run from 0 to 1, not percent.
- **Smoothing:** objects that take mix or level parameters smooth them internally, over about 10 to 20 ms, so you can pass slider values straight in without zipper noise.

## Library reference

### freqshift.jsfx-inc

#### gs_hilbert: 90-degree phase splitter

- `gs_hilbert_init()`
- `gs_hilbert_do(x)` sets `this.i` (the in-phase part) and `this.q` (90 degrees behind).

It is built from two chains of four all-pass sections (Olli Niemitalo's design) and adds no latency. The mirror image of a frequency shift made with it is 47 to 63 dB down from 41 Hz to 5 kHz.

#### gs_shift: one frequency-shifted copy

- `gs_shift_init()`
- `gs_shift_do(i, q, hz)` returns `i` and `q` shifted by `hz`; a negative `hz` shifts down.

Each copy keeps its own phase, so several copies can move independently.

#### gs_lfo: low-frequency oscillator

- `gs_lfo_init(phase)` takes the starting phase, 0 to 1.
- `gs_lfo_do(rate, shape)` returns -1 to 1. `rate` is in Hz. The shapes are:
  - 0: sine.
  - 1: triangle.
  - 2: random step, which jumps to a new random value each cycle and holds it.
  - 3: random smooth, which glides in a straight line from one random point to the next.

#### gs_ensemble: chorus-like ensemble

- `gs_ensemble_init()`
- `gs_ensemble_do(x, hz, copies, mix, spread, lfo_rate, lfo_depth, lfo_shape)` sets `this.l` and `this.r`.
  - `x` is the mono input.
  - `hz` is the shift.
  - `copies` is 0 for one copy shifted up, or 1 for two copies, up and down.
  - `mix` runs from 0 to 1.
  - `spread`, from 0 to 1, pans the up copy left and the down copy right. It only works with two copies.
  - `lfo_depth`, from 0 to 1, wobbles each copy's shift by up to that share of `hz`, from its own LFO.

Shifts of a few Hz give an ensemble effect. Large shifts sound metallic.

### vibrato.jsfx-inc

#### gs_vibrato: stereo delay-line vibrato

- `gs_vibrato_init()`
- `gs_vibrato_do(l, r, cents, rate, shape, gain)` sets `this.l` and `this.r`.
  - `cents` is the peak swing.
  - `rate` is in Hz.
  - `shape` is 0 sine, 1 triangle, 2 random step or 3 random smooth.
  - `gain`, from 0 to 1, scales the swing. Use it for a delayed onset or a fade-in.

**Shapes describe the pitch heard.** A delay line changes pitch according to how fast the delay changes, not according to the delay itself. So each shape here is the delay curve whose rate of change has that shape. For example, a triangle shape uses parabolic delay segments. Using an ordinary triangle as the delay would give a square-wave pitch.

**Latency:** it adds a delay of about 1 ms at 5.5 Hz and 50 cents, and up to about 30 ms at slow, deep settings. A mix with the dry signal below 100% will comb-filter slightly.

**Measured depth:** 50 cents set gives 52 cents measured for sine and triangle. The random shapes are "up to" values.

### vowel.jsfx-inc

#### gs_vowel: three-formant vowel filter

- `gs_vowel_init()`
- `gs_vowel_do(x, t, v_start, v_end, q, mix)` returns the output.
  - `t`, from 0 to 1, is the position between the start vowel and the end vowel. Drive it with an envelope for "wah-ow" sounds.
  - The vowels are 0 A (father), 1 E (bed), 2 I (beet), 3 O (bought) and 4 U (boot).
  - `q` is the band sharpness. 2.5 is even from note to note; 9 to 16 is strongly vocal but uneven.
  - `mix` runs from 0 to 1.

It uses typical adult male formants (Peterson and Barney, 1952), gliding on a log scale.

**Level:** a 1.5 s level match, up to +24 dB, keeps the output at the input's level. It is slow on purpose: a fast level match chases each note, which was heard as the level moving after each pick.

### tracker.jsfx-inc

#### gs_tracker: monophonic pitch tracker

- `gs_tracker_init(fmin, fmax)` takes the range in Hz. gitSynth uses 70 and 1400.
- `gs_tracker_do(x)` should be called every sample with the conditioned input. A 70 Hz high-pass first is recommended.
- After each call:
  - `this.fresh` is 1 on the samples where a new estimate was made, about every 1.3 ms.
  - `this.hz` is the latest estimate in Hz.
  - `this.aper` is its aperiodicity, from 0 (a clean pitch) to 1 (noise). Accept estimates below about 0.2.

**How it works:**

1. It low-passes at 3 kHz and decimates to about 12 kHz.
2. It runs YIN, with a window of 1.5 periods for each candidate period, so high notes are found sooner.
3. It refines the result with parabolic interpolation.
4. A harmonic check below 400 Hz stops low strings being read on their 2nd or 3rd harmonic.

**Measured on guitar:** it finds the note 6 to 16 ms after the pick, and the median error is about 1 cent.

**What it does not do:** it has no note logic. Holding notes, ignoring pick noise and handling mutes belong in the plugin; see `gitSynth-part2.jsfx` for a tested version. Chords are not supported.

#### gs_pll: experimental fine tracker

- `gs_pll_init()`
- `gs_pll_do(x, seed_hz, reseed)` sets `this.hz`, `this.locked` and `this.alive`.

It times each cycle from its zero crossings, after band-pass filtering around the seed pitch. **It is not recommended:** it measured 3 to 4 cents flat, with more wobble than `gs_tracker` on high notes; see `notes/fine-tracker-step13.md`.

### flute.jsfx-inc

#### gs_flute: waveguide flute

- `gs_flute_init()`
- `gs_flute_do(hz, pressure, noise, pink)` returns one sample, with its DC offset removed.
  - `pressure`: the tone starts above about 0.8, and is strong and in tune from 0.9 to 1.2.
  - `noise`: breath noise as a share of the pressure; realistic values are up to about 0.05. Shape it over each note in your plugin: strong at the start, fading as the tone takes over.
  - `pink`: 1 for pink noise, which is mellower, or 0 for white.

It is Julius Smith's flute, as in Romain Michon's Faust-STK port. The bore delay is the period minus 3 samples; the measured loop excess is 1 sample. It plays within about 8 cents from 110 to 1320 Hz.

**Ramp the pressure:** set a target pressure for each note and ramp towards it over a few ms. Ramp it to 0 quickly when the note ends.

**Range:** a real flute plays from C4 to C7. Driven by guitar, an octave of transposition usually sounds most natural.

## Pitfalls

- **EEL2 names are not case-sensitive.** `A1` and `a1` are the same variable.
- **cookDSP's `tanh`** has no overflow guard: it returns NaN for inputs above about 350. Clamp the input, or write your own.
- **cookDSP's `wrap`** loops forever on negative input when its minimum is 0.
- **cookDSP defines `onset`, `delay`, `random`, `gate` and other functions.** Avoid those names for your own variables and functions.
- **Two cookDSP objects aren't suitable for live pitch tracking:**
  - cookDSP's `yin` analyses in fixed blocks, which adds 40 to 85 ms of delay at the sizes guitar needs. Its fallback path has a typo (`buk` for `buf`).
  - cookDSP's `grains` switches between recording and playing with no crossfade.
- **Testing oscillators:** a delay loop fed with noise shows a pitch even when nothing is oscillating. To test a physical model, switch its noise off after the note starts and check that the tone carries on.
- **Remove DC before spectral analysis,** or the strongest "peak" will be 0 Hz.

## Performance

- **Function calls cost little.** EEL2 compiles user functions inline, and `this.` variables are resolved when the plugin compiles, so splitting code into objects adds little or no run-time cost. The cost that does matter is memory arrays in inner loops. Prefer plain `this.` variables for state that is used every sample, such as filter memories.
- **Measured:** a whole gitSynth Part 1 chain, or Part 2 with the tracker and flute, renders 80 seconds of audio in about a second, within the time REAPER takes to start.
- **The heaviest part is the tracker's YIN loop:** about 23,000 multiply-adds every 1.3 ms. If you need several trackers, raise `GS_TRK_HOP`.

## Adding a library

1. Create `lib/<name>.jsfx-inc`, starting with a header comment:
   - one line saying what it is
   - what it needs (normally "cookdsp, imported before this file")
   - every object's functions, parameters and units
   - how it works, and any measured results
2. Put all functions and constants after `@init`.
3. Name functions `gs_<object>_init` and `gs_<object>_do`. Name constants `GS_<LIBRARY>_<NAME>`.
4. Allocate memory with `memalloc` inside `_init` only, never in `@sample`.
5. Use no globals. Pass everything in as parameters, and return results or set `this.` fields.
6. Add a section to this README and a row to the table above.
7. Test it with the rig (see below) before relying on it.

## Testing

The repository's `tools` folder renders clips through the real JSFX using REAPER from the command line, then measures the result; see the [main README](../../README.md#testing). Python copies of DSP code are useful for exploring an idea, but only a render of the JSFX tests the plugin itself.

## Credits

- **cookDSP:** Olivier Bélanger, permissive licence; see its files.
- **Hilbert all-pass coefficients:** Olli Niemitalo.
- **Flute:** Julius O. Smith's algorithm, after Romain Michon's Faust-STK port (STK-4.3 licence, MIT style).
- **Pink noise filter:** Paul Kellet.
- **YIN:** A. de Cheveigné and H. Kawahara (2002).
- **Formant values:** G. E. Peterson and H. L. Barney (1952).
