"""Render every clip through the tracker test plugin and compare with the
reference pitch. Prints one summary line per clip, plus a total.

Usage: python tools/track_all.py [--set NAME=VALUE ...]
Save the output under notes/ to keep a baseline, for example:
  python tools/track_all.py > notes/tracker-step11.txt
"""
import glob
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import render                     # noqa: E402
from compare_pitch import compare             # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    settings = dict(s.split("=", 1) for s in sys.argv[1:] if s != "--set")
    everything = []
    for clip in sorted(glob.glob(os.path.join(ROOT, "clips", "*.wav"))):
        name = os.path.splitext(os.path.basename(clip))[0]
        wav = render(clip, "gitSynth-part2.jsfx", "trk-" + name, settings, channels=4)
        res = compare(wav, name)
        everything += res
        locks = [r["lock"] for r in res if r["lock"] is not None]
        print(f"{name:26s} notes {len(res):3d}  locked {len(locks):3d}  "
              f"median lock {1000 * np.median(locks) if locks else float('nan'):5.0f} ms  "
              f"median error {np.nanmedian([r['med'] for r in res]):5.1f} cents  "
              f"octave-error notes {sum(1 for r in res if r['octave'] > 0.01):3d}  "
              f"gaps {100 * np.nanmean([r['gaps'] for r in res]):5.1f}%", flush=True)
    locks = [r["lock"] for r in everything if r["lock"] is not None]
    print(f"{'ALL':26s} notes {len(everything):3d}  locked {len(locks):3d}  "
          f"median lock {1000 * np.median(locks):5.0f} ms  "
          f"median error {np.nanmedian([r['med'] for r in everything]):5.1f} cents  "
          f"octave-error notes {sum(1 for r in everything if r['octave'] > 0.01):3d}  "
          f"gaps {100 * np.nanmean([r['gaps'] for r in everything]):5.1f}%")


if __name__ == "__main__":
    main()
