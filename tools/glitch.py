"""How much of the tracker voice sounds wrong.

Over 10 ms frames where the voice output is above -50 dBFS:
  wrong   the voice's pitch is more than 100 cents from the reference
  after   the reference has no pitch (the note has ended or been muted)
as a share of the sounding frames, and in seconds. The reference is shifted
55 ms later to line up with the picks (pYIN marks notes early).

Usage: python tools/glitch.py RENDER.wav CLIP_NAME
"""
import csv
import os
import sys

import numpy as np
import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHIFT = 0.055


def glitch(render, name):
    y, sr = sf.read(render)
    out, p = y[:, 0], y[:, 2] * 2000
    rows = list(csv.DictReader(open(os.path.join(ROOT, "results", "reference", name + ".csv"))))
    rt = np.array([float(r["time_s"]) for r in rows]) + SHIFT
    rv = np.array([int(r["voiced"]) for r in rows]).astype(bool)
    ry = np.array([float(r["yin_hz"]) for r in rows])
    hop = int(0.01 * sr)
    wrong = after = sounding = 0
    for i in range(0, len(out) - hop, hop):
        lv = 10 * np.log10(np.mean(out[i:i + hop] ** 2) + 1e-12)
        if lv < -50:
            continue
        sounding += 1
        j = np.searchsorted(rt, (i + hop / 2) / sr)
        if j >= len(rt) or not rv[j]:
            after += 1
            continue
        hz = p[i + hop // 2]
        if hz > 0 and abs(1200 * np.log2(hz / ry[j])) > 100:
            wrong += 1
    return wrong, after, sounding, hop / sr


if __name__ == "__main__":
    w, a, s, dt = glitch(sys.argv[1], sys.argv[2])
    print(f"{sys.argv[2]}: wrong pitch {100 * w / s:.1f}% ({w * dt:.2f} s), after note end {100 * a / s:.1f}% ({a * dt:.2f} s)")
