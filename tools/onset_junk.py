# Copyright (C) 2026 Rich Caloggero
# SPDX-License-Identifier: GPL-3.0-or-later
"""Wrong pitch reported near note starts.

For each reference note, over the first 150 ms after its pick: the share of time the
tracker reports a pitch more than 100 cents away from the note (junk), and
the share with no pitch at all (silent). Also the time to lock (within 50
cents for 50 ms), as in compare_pitch.

Usage: python tools/onset_junk.py RENDER.wav CLIP_NAME
"""
import sys

import numpy as np
import soundfile as sf

from compare_pitch import load_reference, notes, compare, pick_times

WINDOW = 0.15


def onset_junk(render, name):
    y, sr = sf.read(render)
    p = y[:, 2] * 2000
    t, v, yin, lev = load_reference(name)
    junk, silent = [], []
    ns = notes(t, v, yin, lev)
    for (_, te, hz), ts in zip(ns, pick_times(name, [n[0] for n in ns])):
        seg = p[int(ts * sr):int(min(te, ts + WINDOW) * sr)]
        on = seg > 0
        cents = np.abs(1200 * np.log2(np.where(on, seg, hz) / hz))
        junk.append(np.mean(on & (cents > 100)))
        silent.append(np.mean(~on))
    locks = [r["lock"] for r in compare(render, name) if r["lock"] is not None]
    return np.mean(junk), np.mean(silent), np.median(locks) if locks else np.nan


if __name__ == "__main__":
    j, s, lk = onset_junk(sys.argv[1], sys.argv[2])
    print(f"{sys.argv[2]}: first 150 ms wrong pitch {100 * j:.1f}%, silent {100 * s:.1f}%, median lock {1000 * lk:.0f} ms")
