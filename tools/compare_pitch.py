"""Compare a rendered tracker debug channel with the reference pitch.

The render's channel 3 holds the tracked pitch (Hz / 2000, 0 = no pitch),
as written by gitSynth-part2.jsfx. The reference is results/reference/CLIP.csv
from tools/reference_pitch.py. For each reference note (a voiced run of at
least 0.25 s, louder than -45 dB) it reports:
  lock    time from the pick until the tracker is within 50 cents
          of the note and stays there for 50 ms
  error   median and 95th-percentile absolute error in cents, measured from
          150 ms into the note to its end
  octave  share of that time more than 600 cents off (octave-type errors)
  gaps    share of that time with no pitch reported

Usage: python tools/compare_pitch.py RENDER.wav CLIP_NAME
"""
import csv
import os
import sys

import numpy as np
import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCK_CENTS = 50
LOCK_HOLD = 0.05
SETTLE = 0.15


def load_reference(name):
    rows = list(csv.DictReader(open(os.path.join(ROOT, "results", "reference", name + ".csv"))))
    t = np.array([float(r["time_s"]) for r in rows])
    voiced = np.array([int(r["voiced"]) for r in rows]).astype(bool)
    yin = np.array([float(r["yin_hz"]) for r in rows])
    level = np.array([float(r["level_db"]) for r in rows])
    return t, voiced, yin, level


def notes(t, voiced, yin, level):
    """Voiced runs, split where the reference pitch jumps by more than
    70 cents between frames (a new note played without a silent gap)."""
    out, start = [], None
    for i in range(len(voiced) + 1):
        v = i < len(voiced) and voiced[i]
        jump = (v and start is not None and i > 0 and yin[i] > 0 and yin[i - 1] > 0
                and abs(1200 * np.log2(yin[i] / yin[i - 1])) > 70)
        if v and start is None:
            start = i
        elif (not v or jump) and start is not None:
            if t[i - 1] - t[start] >= 0.25 and level[start:i].max() > -45:
                n = i - start
                hz = float(np.median(yin[start + n // 4: i - n // 4]))
                out.append((t[start], t[i - 1], hz))
            start = i if jump else None
    return out


def pick_times(name, starts):
    """Actual pick time near each reference note start.

    pYIN analyses 128 ms windows centred on each frame, so it marks a note as
    starting about 50 ms before the pick. The pick is taken as the steepest
    10 ms rise in the clip's 5 ms level within 150 ms of the reference start.
    """
    x, sr = sf.read(os.path.join(ROOT, "clips", name + ".wav"))
    k = int(0.005 * sr)
    e = 10 * np.log10(np.convolve(x ** 2, np.ones(k) / k, "same") + 1e-12)
    d = int(0.01 * sr)
    out = []
    for ts in starts:
        a = max(k, int((ts - 0.15) * sr))
        b = min(len(e), int((ts + 0.15) * sr))
        rise = e[a + d:b] - e[a:b - d]
        out.append((a + d + int(np.argmax(rise))) / sr if len(rise) else ts)
    return out


def compare(render, name):
    y, sr = sf.read(render)
    track = y[:, 2] * 2000
    t, voiced, yin, level = load_reference(name)
    results = []
    ns = notes(t, voiced, yin, level)
    picks = pick_times(name, [n[0] for n in ns])
    for (_, te, hz), ts in zip(ns, picks):
        if te - ts < 0.1:
            continue
        i0, i1 = int(ts * sr), int(te * sr)
        seg = track[i0:i1]
        cents = np.where(seg > 0, 1200 * np.log2(np.maximum(seg, 1e-6) / hz), np.nan)
        ok = np.abs(np.nan_to_num(cents, nan=1e9)) < LOCK_CENTS
        hold = int(LOCK_HOLD * sr)
        lock = None
        run = np.convolve(ok, np.ones(hold, dtype=int), "valid")
        hit = np.nonzero(run == hold)[0]
        if len(hit):
            lock = hit[0] / sr
        steady = cents[int(SETTLE * sr):]
        found = steady[~np.isnan(steady)]
        results.append(dict(
            start=ts, hz=hz, lock=lock,
            med=float(np.median(np.abs(found))) if len(found) else np.nan,
            p95=float(np.percentile(np.abs(found), 95)) if len(found) else np.nan,
            octave=float(np.mean(np.abs(found) > 600)) if len(found) else np.nan,
            gaps=float(np.mean(np.isnan(steady))) if len(steady) else np.nan))
    return results


def main():
    render, name = sys.argv[1], sys.argv[2]
    res = compare(render, name)
    print(f"{name}: {len(res)} notes")
    for r in res:
        lock = f"{1000 * r['lock']:5.0f} ms" if r["lock"] is not None else "  never"
        print(f"  {r['start']:6.2f} s {r['hz']:7.1f} Hz  lock {lock}  error {r['med']:5.1f} / {r['p95']:6.1f} cents"
              f"  octave {100 * r['octave']:4.1f}%  gaps {100 * r['gaps']:4.1f}%")
    locks = [r["lock"] for r in res if r["lock"] is not None]
    print(f"  summary: locked {len(locks)}/{len(res)}, median lock {1000 * np.median(locks):.0f} ms, "
          f"median error {np.nanmedian([r['med'] for r in res]):.1f} cents, "
          f"notes with octave errors {sum(1 for r in res if r['octave'] > 0.01)}, "
          f"mean gaps {100 * np.nanmean([r['gaps'] for r in res]):.1f}%")


if __name__ == "__main__":
    main()
