"""Render every clip through the tracker test plugin and compare with the
reference pitch. Prints one summary line per clip, plus a total.

All clips are rendered in one REAPER run (one track each, as stems).

Usage: python tools/track_all.py [NAME=VALUE ...]
Save the output under notes/ to keep a baseline, for example:
  python tools/track_all.py > notes/tracker-step11.txt
"""
import glob
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import render_batch                # noqa: E402
from compare_pitch import compare             # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN = "gitSynth-part2.jsfx"


def line(label, res):
    locks = [r["lock"] for r in res if r["lock"] is not None]
    return (f"{label:26s} notes {len(res):3d}  locked {len(locks):3d}  "
            f"median lock {1000 * np.median(locks) if locks else float('nan'):5.0f} ms  "
            f"median error {np.nanmedian([r['med'] for r in res]):5.1f} cents  "
            f"octave-error notes {sum(1 for r in res if r['octave'] > 0.01):3d}  "
            f"gaps {100 * np.nanmean([r['gaps'] for r in res]):5.1f}%")


def main():
    settings = dict(s.split("=", 1) for s in sys.argv[1:] if s != "--set")
    clips = sorted(glob.glob(os.path.join(ROOT, "clips", "*.wav")))
    names = [os.path.splitext(os.path.basename(c))[0] for c in clips]
    jobs = [(c, PLUGIN, settings, "trk-" + n) for c, n in zip(clips, names)]
    wavs = render_batch(jobs, "trk-all", channels=4)
    everything = []
    for name, wav in zip(names, wavs):
        res = compare(wav, name)
        everything += res
        print(line(name, res), flush=True)
    print(line("ALL", everything))


if __name__ == "__main__":
    main()
