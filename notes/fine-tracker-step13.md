# Fine tracker (step 13), first attempt: findings

Date: 2026-10-24. Code: `gs_pll_*` in `jsfx/lib/tracker.jsfx-inc`;
switch in `jsfx/gitSynth-part2.jsfx`, slider 5 (default: coarse only).

## Design tried

Two band-pass stages (Q 1.5) centred on the coarse pitch isolate the
fundamental; a zero crossing with hysteresis times each cycle to a fraction
of a sample; pitch = average of the cycles in about the last 10 ms (2-16).
The coarse tracker (YIN) seeds it at each attack and restarts it when they
disagree by more than 150 cents for about 50 ms.

## Results on the clips (median per note, steady part of the note)

| Measure | Coarse only | Coarse + fine |
|---|---|---|
| Error against reference | about 1 cent | 2-5 cents |
| Offset | about 0 | 3-4 cents flat, every clip |
| Wobble, low E clip | 0.8 cents | 0.6 cents |
| Wobble, high E clip | 1.0 cents | 3.6-4.3 cents |
| Lock time | 57 ms | unchanged (waits for the coarse seed) |

On high notes the fine pitch wobbles regularly at about 30 Hz, about 3 cents.

## Ruled out

- Timing noise of short cycles: averaging up to 16 cycles barely helped.
- Lock flicker switching the output between trackers: lock hysteresis and
  holding the fine pitch while it is alive did not change the wobble.
- Feedback from re-centring the band-pass: slowing it tenfold changed nothing.

## Not yet known

- The cause of the steady flat offset and the 30 Hz wobble.
- Whether the coarse tracker lags on bends and vibrato: no clip with bends,
  vibrato or legato has been recorded yet (RECORDING.md lists them).

## Conclusion so far

The coarse tracker is already more accurate and steadier than this fine
tracker, and the fine tracker cannot shorten the lock time while it depends
on the coarse seed. Judge whether a fine tracker is needed at all with a
bends/vibrato/legato clip; the bigger gap is the lock time at note starts.
