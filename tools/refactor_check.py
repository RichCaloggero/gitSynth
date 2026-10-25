# Copyright (C) 2026 Rich Caloggero
# SPDX-License-Identifier: GPL-3.0-or-later
"""Render fixed test cases through every plugin and compare with a baseline.

Used while reorganising code: the output must not change. Settings avoid
random numbers (random LFO shapes, breath noise) so renders are repeatable.

  python tools/refactor_check.py save      render and keep as the baseline
  python tools/refactor_check.py           render and compare with it
"""
import os
import shutil
import sys

import numpy as np
import soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import render_batch, ROOT  # noqa: E402

CASES = [
    ("04-dynamics", "gitSynth-part1.jsfx", {}, "p1-default"),
    ("04-dynamics", "gitSynth-part1.jsfx", {
        "swell_ms": 80, "sustain": 80, "sus_margin_db": 0, "drive_db": 20, "shape": 2,
        "body_amt": 60, "vow_mix": 100, "ens_mix": 40, "ens_copies": 1, "ens_spread": 70,
        "vib_cents": 25, "reso": 30, "depth_oct": 4}, "p1-full"),
    ("06-mutes-and-staccato", "gitSynth-part1.jsfx", {"env_mode": 1, "shape": 1, "drive_db": 12}, "p1-hold"),
    ("02a-chromatic-lowE", "gitSynth-part2.jsfx", {"wave": 2}, "p2-saw"),
    ("09-mutes-live", "gitSynth-part2.jsfx", {"wave": 0, "pitch_mode": 1, "glide_ms": 40, "transpose": 12}, "p2-sine"),
    ("11-B-string", "gitSynth-part2.jsfx", {"wave": 5, "fl_noise_on": 0, "fl_noise_hold": 0}, "p2-flute"),
    ("01-open-strings", "gitSynth-tuner.jsfx", {}, "tuner"),
    ("04-dynamics", "gitSynth-freqshift.jsfx", {"ens_mix": 50}, "freqshift"),
]
BASE = os.path.join(ROOT, "results", "baseline")


def main():
    jobs = [(os.path.join(ROOT, "clips", c + ".wav"), p, s, "rc-" + n) for c, p, s, n in CASES]
    wavs = render_batch(jobs, "refactor-check", channels=4)
    if sys.argv[1:] == ["save"]:
        os.makedirs(BASE, exist_ok=True)
        for (_, _, _, n), w in zip(CASES, wavs):
            shutil.copy(w, os.path.join(BASE, n + ".wav"))
        print("baseline saved")
        return
    worst = -999
    for (_, p, _, n), w in zip(CASES, wavs):
        a, _ = sf.read(os.path.join(BASE, n + ".wav"))
        b, _ = sf.read(w)
        m = min(len(a), len(b))
        ref = np.sqrt(np.mean(a[:m, :2] ** 2)) + 1e-12
        diff = np.sqrt(np.mean((a[:m] - b[:m]) ** 2, axis=0)) / ref
        db = 20 * np.log10(np.max(diff) + 1e-15)
        worst = max(worst, db)
        print(f"{n:12s} {p:26s} difference {db:7.1f} dB (all channels, relative to the signal)")
    print("SAME" if worst < -100 else "CHANGED", f"(worst {worst:.1f} dB; below -100 dB counts as the same)")


if __name__ == "__main__":
    main()
