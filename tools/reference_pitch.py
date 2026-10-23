"""Reference pitch for gitSynth test clips.

For each WAV, writes results/reference/<clip>.csv with one row per frame
(time, pYIN pitch, voiced flag, voiced probability, YIN pitch, level),
and prints a per-note summary: start time, pitch, nearest note, cents off.

pYIN decides where notes are; plain YIN gives the precise pitch, because
pYIN's pitch is quantised to 10-cent steps at its default resolution
(and a finer resolution makes it mark almost nothing as voiced).

Usage: python tools/reference_pitch.py [clip.wav ...]   (default: clips/*.wav)
"""
import csv
import glob
import os
import sys

import numpy as np
import librosa

SR = 16000          # analysis rate; ample for fundamentals up to ~1.5 kHz
HOP = 256           # 16 ms per frame
FRAME = 2048
FMIN, FMAX = 70, 1500
MIN_FRAMES = 15     # shortest note reported, about 0.25 s
MIN_DB = -45        # ignore quieter "notes" (hum, buzz)

NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def note_name(hz):
    midi = 69 + 12 * np.log2(hz / 440.0)
    near = int(round(midi))
    return NAMES[near % 12] + str(near // 12 - 1), (midi - near) * 100


def analyse(path, out_dir):
    y, _ = librosa.load(path, sr=SR, mono=True)
    if not np.any(y):
        print(f"{os.path.basename(path)}: silent, skipped")
        return
    f0, voiced, prob = librosa.pyin(y, fmin=FMIN, fmax=FMAX, sr=SR,
                                    frame_length=FRAME, hop_length=HOP)
    fine = librosa.yin(y, fmin=FMIN, fmax=FMAX, sr=SR,
                       frame_length=FRAME, hop_length=HOP)
    rms = librosa.feature.rms(y=y, frame_length=FRAME, hop_length=HOP)[0]
    db = 20 * np.log10(rms + 1e-12)
    t = librosa.times_like(f0, sr=SR, hop_length=HOP)

    name = os.path.splitext(os.path.basename(path))[0]
    with open(os.path.join(out_dir, name + '.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['time_s', 'pyin_hz', 'voiced', 'voiced_prob', 'yin_hz', 'level_db'])
        for i in range(len(t)):
            w.writerow([f"{t[i]:.4f}", '' if np.isnan(f0[i]) else f"{f0[i]:.3f}",
                        int(voiced[i]), f"{prob[i]:.3f}", f"{fine[i]:.3f}", f"{db[i]:.1f}"])

    # Group voiced frames into notes; measure the middle half to skip the attack.
    print(f"{name}:")
    cents_all = []
    start = None
    for i in range(len(voiced) + 1):
        v = i < len(voiced) and voiced[i]
        if v and start is None:
            start = i
        elif not v and start is not None:
            if i - start >= MIN_FRAMES:
                n = i - start
                lo, hi = start + n // 4, i - n // 4
                hz = float(np.median(fine[lo:hi]))
                level = float(np.max(db[start:i]))
                if level > MIN_DB:
                    note, cents = note_name(hz)
                    cents_all.append(cents)
                    print(f"  {t[start]:6.1f} s  {hz:7.2f} Hz  {note:4s} {cents:+6.1f} cents")
            start = None
    if cents_all:
        print(f"  median offset {np.median(cents_all):+.1f} cents over {len(cents_all)} notes")


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    paths = sys.argv[1:] or sorted(glob.glob(os.path.join(root, 'clips', '*.wav')))
    out_dir = os.path.join(root, 'results', 'reference')
    os.makedirs(out_dir, exist_ok=True)
    for p in paths:
        analyse(p, out_dir)


if __name__ == '__main__':
    main()
